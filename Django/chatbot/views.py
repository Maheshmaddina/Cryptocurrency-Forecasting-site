import json
import os
import sys
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# Import the main prediction function from the predict app
from predict.views import get_prediction

SUPPORTED_COINS = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX"]

@csrf_exempt
def chatbot_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '').lower()
            context = data.get('context', {})

            # Handle initial greeting
            if message == 'init':
                context = {'awaiting': 'initial_choice'}
                return JsonResponse({
                    'message': 'Hello! I am CryptoSight. How can I help you today?',
                    'options': ['Get Prediction', 'Check Price'],
                    'context': context
                })

            # Check for reset command
            if 'reset' in message or 'start over' in message:
                context = {}
                return JsonResponse({
                    'message': 'Okay, let\'s start over. How can I help you?',
                    'context': context
                })

            # --- Universal "Go Back" command ---
            if 'go back' in message:
                if context.get('awaiting') == 'interval':
                    context['awaiting'] = 'coin'
                    return JsonResponse({ 'message': 'Okay, which cryptocurrency would you like to predict?', 'options': SUPPORTED_COINS, 'context': context })
                elif context.get('awaiting') == 'steps':
                    context['awaiting'] = 'interval'
                    return JsonResponse({ 'message': 'No problem. Do you want a daily or hourly prediction?', 'options': ['Daily', 'Hourly'], 'context': context })

            # --- Handle initial user choice ---
            if context.get('awaiting') == 'initial_choice':
                if 'prediction' in message:
                    context['awaiting'] = 'coin'
                    return JsonResponse({
                        'message': 'Sure, I can help with that! Which cryptocurrency would you like to predict?',
                        'options': SUPPORTED_COINS,
                        'context': context
                    })
                elif 'price' in message:
                    context['awaiting'] = 'price_check_coin'
                    return JsonResponse({
                        'message': 'Which cryptocurrency would you like to check the price for?',
                        'options': SUPPORTED_COINS,
                        'context': context
                    })

            # --- Prediction Flow ---
            if context.get('awaiting') == 'price_check_coin':
                coin = message.upper()
                if coin in SUPPORTED_COINS:
                    from predict.prediction import get_realtime_price
                    usd_to_inr = float(os.environ.get('USD_TO_INR', '88.75'))
                    price = get_realtime_price(coin, usd_to_inr)
                    response_message = f"The current price of <b>{coin}</b> is <b>₹{price:,.2f}</b>." if price else f"Sorry, I couldn't fetch the price for {coin} right now."

                    # After checking price, return to the main menu
                    context['awaiting'] = 'initial_choice'
                    return JsonResponse({
                        'message': response_message + "<br><br><small><i>Note: Prices are sourced from Binance and may differ slightly from other platforms.</i></small><br><br>What would you like to do next?",
                        'options': ['Get Prediction', 'Check Price'],
                        'context': context
                    })

            if context.get('awaiting') == 'coin':
                coin = message.upper()
                if coin in SUPPORTED_COINS:
                    context['coin'] = coin
                    context['awaiting'] = 'interval'
                    return JsonResponse({
                        'message': f"Great! For {coin}. Do you want a daily or hourly prediction?",
                        'options': ['Daily', 'Hourly', 'Go Back'],
                        'context': context
                    })
                else:
                    return JsonResponse({
                        'message': f"Sorry, I don't support {coin}. Please choose from: {', '.join(SUPPORTED_COINS)}.",
                        'options': SUPPORTED_COINS,
                        'context': context
                    })

            elif context.get('awaiting') == 'interval':
                interval_map = {'daily': '1d', 'hourly': '1h'}
                if message in interval_map:
                    context['interval'] = interval_map[message]
                    context['awaiting'] = 'steps'

                    # Make the example message context-aware
                    if message == 'daily':
                        example_text = "e.g., 7 days"
                    else:  # hourly
                        example_text = "e.g., 12 hours"

                    return JsonResponse({
                        'message': f'Got it. How many steps ({example_text}) ahead should I predict?',
                        'options': ['Go Back'],
                        'context': context
                    })
                else:
                    return JsonResponse({
                        'message': "Please choose either 'Daily' or 'Hourly'.",
                        'options': ['Daily', 'Hourly', 'Go Back'],
                        'context': context
                    })

            elif context.get('awaiting') == 'steps':
                try:
                    steps = int(message)
                    interval = context.get('interval')
                    is_valid = (interval == '1h' and 1 <= steps <= 23) or \
                                (interval == '1d' and 1 <= steps <= 30)

                    if is_valid:
                        context['steps'] = steps
                        context['awaiting'] = None # End of questions

                        # --- Execute Prediction ---
                        coin = context.get('coin')
                        timeframe = 'hourly' if interval == '1h' else 'daily'

                        try:
                            # Use the powerful get_prediction function
                            prediction_data = get_prediction(coin, timeframe, steps)

                            # Handle pluralization for the response text
                            unit = 'day' if timeframe == 'daily' else 'hour'
                            plural_unit = f"{unit}s" if steps > 1 else unit

                            # Format a rich response using a table for proper alignment
                            response_text = (
                                f"📈 <b>Prediction for {coin} ({steps} {plural_unit})</b><br><br>"
                                "<div style='display: flex; justify-content: center;'>"
                                    "<table style='border-spacing: 0 5px; width: 90%;'>"
                                        f"<tr><td style='width: 120px;'><b>Current Price</b></td><td style='width: 10px;'>:</td><td>₹{prediction_data['current_price']:,.2f}</td></tr>"
                                        f"<tr><td><b>Predicted Price</b></td><td>:</td><td>₹{prediction_data['predicted_price']:,.2f}</td></tr>"
                                        f"<tr><td><b>Confidence</b></td><td>:</td><td>{prediction_data['confidence_level']}%</td></tr>"
                                        f"<tr><td><b>Market Sentiment</b></td><td>:</td><td>{prediction_data['market_sentiment']}</td></tr>"
                                    "</table>"
                                "</div>"
                            )

                        except Exception as e:
                            print(f"Chatbot prediction failed: {e}")
                            response_text = "Sorry, I couldn't generate a prediction at this time. The model might be unavailable. Please try again later."

                        # Ask for the next action instead of resetting
                        context['awaiting'] = 'another_prediction'
                        full_response = response_text + "<br><br><small><i>Note: Prices are sourced from Binance and may differ slightly from other platforms.</i></small><br><br>Would you like to start another prediction?"

                        return JsonResponse({
                            'message': full_response,
                            'options': ['New Prediction', 'No Thanks'],
                            'context': context
                        })

                    else:
                        limit = 23 if context.get('interval') == '1h' else 30
                        return JsonResponse({
                            'message': f'Please enter a number between 1 and {limit}.',
                            'options': ['Go Back'],
                            'context': context
                        })
                except ValueError:
                    return JsonResponse({
                        'message': 'That doesn\'t look like a number. Please enter how many steps to predict.',
                        'options': ['Go Back'],
                        'context': context
                    })

            elif context.get('awaiting') == 'another_prediction':
                if 'new' in message or 'yes' in message:
                    # Start a new prediction flow
                    context = {'awaiting': 'coin'}
                    return JsonResponse({
                        'message': 'Great! Which cryptocurrency would you like to predict?',
                        'options': SUPPORTED_COINS,
                        'context': context
                    })
                elif 'no' in message:
                    # End the conversation and offer to start a new one
                    context = {} # Clear context to end the current flow
                    return JsonResponse({
                        'message': 'You got it! Feel free to ask for another prediction or anything else.',
                        'options': ['Get Prediction', 'Check Price'],
                        'context': context
                    })
                else:
                    # Handle unexpected input in this state
                    return JsonResponse({
                        'message': "I'm sorry, I didn't understand that. Would you like to start a new prediction or not?",
                        'options': ['New Prediction', 'No Thanks', 'Go Back'],
                        'context': context # Keep the current context
                    })

            # --- Glossary / Definitions ---
            if message.startswith('what is') or message.startswith('define'):
                definitions = {
                    'market sentiment': 'Market sentiment refers to the overall attitude of investors toward a particular security or financial market. It is the feeling or tone of a market, or its crowd psychology, as revealed through the activity and price movement.',
                    'lstm': 'LSTM stands for Long Short-Term Memory. It is a type of recurrent neural network (RNN) architecture that is well-suited for time-series data, like stock prices, because it can remember patterns over long sequences.',
                    'volatility': 'Volatility is a statistical measure of the dispersion of returns for a given security or market index. In simple terms, higher volatility means that a security\'s price can change dramatically over a short time period in either direction.'
                }
                for term, definition in definitions.items():
                    if term in message:
                        return JsonResponse({
                            'message': f"<b>{term.title()}:</b><br>{definition}",
                            'context': context
                        })

            # --- Initial Keywords ---
            if 'predict' in message or 'forecast' in message:
                context['awaiting'] = 'coin'
                return JsonResponse({
                    'message': 'Sure, I can help with that! Which cryptocurrency would you like to predict?',
                    'options': SUPPORTED_COINS,
                    'context': context
                })
            elif 'check price' in message: 
                context['awaiting'] = 'price_check_coin'
                return JsonResponse({
                    'message': 'Which cryptocurrency would you like to check the price for?',
                    'options': SUPPORTED_COINS,
                    'context': context
                })


            # --- Default Response ---
            return JsonResponse({
                'message': "I can help with cryptocurrency predictions. Try saying 'predict bitcoin'.",
                'context': context
            })

        except Exception as e:
            return JsonResponse({'message': f'An error occurred: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)