"""
Pure-numpy inference for the trained LSTM models.

The .keras models and MinMax scalers are exported to .npz files by
Model_Training/export_numpy_weights.py. This module mirrors Keras' LSTM,
BatchNormalization and Dense layers at inference time (Dropout is a no-op),
so the web app runs without TensorFlow - which is far too large for Vercel.
"""
import numpy as np


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _lstm(x, kernel, recurrent, bias, return_sequences):
    """Keras LSTM forward pass (gate order: input, forget, cell, output)"""
    batch, steps, _ = x.shape
    units = recurrent.shape[0]
    h = np.zeros((batch, units), dtype=x.dtype)
    c = np.zeros((batch, units), dtype=x.dtype)

    # Input projections for every timestep at once
    x_proj = x @ kernel + bias
    outputs = []
    for t in range(steps):
        z = x_proj[:, t] + h @ recurrent
        i = _sigmoid(z[:, :units])
        f = _sigmoid(z[:, units:2 * units])
        g = np.tanh(z[:, 2 * units:3 * units])
        o = _sigmoid(z[:, 3 * units:])
        c = f * c + i * g
        h = o * np.tanh(c)
        if return_sequences:
            outputs.append(h)

    return np.stack(outputs, axis=1) if return_sequences else h


class MinMaxScalerParams:
    """Drop-in for a fitted sklearn MinMaxScaler's transform/inverse_transform"""

    def __init__(self, min_, scale_):
        self.min_ = min_
        self.scale_ = scale_

    def transform(self, X):
        return np.asarray(X, dtype=np.float64) * self.scale_ + self.min_

    def inverse_transform(self, X):
        return (np.asarray(X, dtype=np.float64) - self.min_) / self.scale_


class NumpyLSTMModel:
    """Loads an exported .npz model and predicts like keras Model.predict"""

    def __init__(self, path):
        with np.load(path, allow_pickle=False) as data:
            self.window = int(data['window'])
            self.scaler = MinMaxScalerParams(data['scaler_min'], data['scaler_scale'])
            self.layers = []
            for index, kind in enumerate(data['layers']):
                prefix = f'l{index}_'
                params = {key[len(prefix):]: data[key] for key in data.files if key.startswith(prefix)}
                self.layers.append((str(kind), params))

    def predict(self, x):
        """x: (batch, timesteps, features) -> (batch, outputs)"""
        out = np.asarray(x, dtype=np.float32)
        for kind, p in self.layers:
            if kind == 'LSTM':
                out = _lstm(out, p['kernel'], p['recurrent'], p['bias'], bool(p['return_sequences']))
            elif kind == 'BatchNormalization':
                out = (out - p['mean']) / np.sqrt(p['var'] + p['epsilon']) * p['gamma'] + p['beta']
            elif kind == 'Dense':
                out = out @ p['kernel'] + p['bias']
            else:
                raise ValueError(f"Unsupported layer type: {kind}")
        return out
