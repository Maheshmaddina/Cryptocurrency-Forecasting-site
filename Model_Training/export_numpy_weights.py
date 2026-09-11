"""
Export the trained Keras LSTM models and their MinMax scalers to .npz files.

The Django app runs these with plain numpy (Django/predict/lstm_numpy.py), so the
deployed site doesn't need TensorFlow. Re-run after retraining any model:

    python Model_Training/export_numpy_weights.py

Each exported model is checked against TensorFlow's own output before it's saved.
"""
import os
import sys
import glob
import numpy as np
import joblib
import tensorflow as tf

ROOT = os.path.dirname(os.path.abspath(__file__))
DJANGO_DIR = os.path.join(os.path.dirname(ROOT), 'Django')
sys.path.insert(0, DJANGO_DIR)

from predict.lstm_numpy import NumpyLSTMModel  # noqa: E402


def export_model(model_path, scaler_path, out_path):
    model = tf.keras.models.load_model(model_path, compile=False)
    scaler = joblib.load(scaler_path)

    arrays = {
        'window': np.array(model.input_shape[1]),
        'scaler_min': scaler.min_,
        'scaler_scale': scaler.scale_,
    }
    layer_types = []
    for layer in model.layers:
        kind = type(layer).__name__
        cfg = layer.get_config()
        weights = layer.get_weights()
        if kind == 'Dropout':
            continue  # inactive at inference
        prefix = f'l{len(layer_types)}_'
        if kind == 'LSTM':
            assert cfg['activation'] == 'tanh' and cfg['recurrent_activation'] == 'sigmoid'
            assert cfg.get('use_bias', True)
            arrays[prefix + 'kernel'], arrays[prefix + 'recurrent'], arrays[prefix + 'bias'] = weights
            arrays[prefix + 'return_sequences'] = np.array(cfg['return_sequences'])
        elif kind == 'BatchNormalization':
            assert cfg.get('center', True) and cfg.get('scale', True)
            gamma, beta, mean, var = weights
            arrays.update({prefix + 'gamma': gamma, prefix + 'beta': beta,
                           prefix + 'mean': mean, prefix + 'var': var,
                           prefix + 'epsilon': np.array(cfg['epsilon'], dtype=np.float32)})
        elif kind == 'Dense':
            assert cfg['activation'] == 'linear'
            arrays[prefix + 'kernel'], arrays[prefix + 'bias'] = weights
        else:
            raise ValueError(f"{model_path}: unsupported layer {kind}")
        layer_types.append(kind)
    arrays['layers'] = np.array(layer_types)

    np.savez_compressed(out_path, **arrays)

    # Verify the numpy engine reproduces TensorFlow's predictions
    sample = np.random.default_rng(0).random((4,) + tuple(model.input_shape[1:]), dtype=np.float32)
    expected = model.predict(sample, verbose=0)
    actual = NumpyLSTMModel(out_path).predict(sample)
    max_diff = float(np.max(np.abs(expected - actual)))
    if max_diff > 1e-4:
        os.remove(out_path)
        raise AssertionError(f"{out_path}: numpy output differs from TensorFlow by {max_diff}")
    return max_diff


if __name__ == '__main__':
    for timeframe in ('hourly', 'daily'):
        src_dir = os.path.join(ROOT, f'models_{timeframe}')
        out_dir = os.path.join(DJANGO_DIR, 'predict', f'models_{timeframe}')
        for model_path in sorted(glob.glob(os.path.join(src_dir, f'*_{timeframe}_lstm.keras'))):
            symbol = os.path.basename(model_path).split('_')[0]
            scaler_path = os.path.join(src_dir, f'{symbol}_scaler.pkl')
            out_path = os.path.join(out_dir, f'{symbol}_{timeframe}_lstm.npz')
            max_diff = export_model(model_path, scaler_path, out_path)
            print(f"{symbol} {timeframe}: exported, max diff vs TensorFlow {max_diff:.2e}")
