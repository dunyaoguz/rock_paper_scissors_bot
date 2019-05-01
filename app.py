import pickle
import pandas as pd
import flask
import numpy as np
from collections import Counter
from flask import render_template
from itertools import islice

smart_bot = pickle.load(open('bots/model.pkl', 'rb'))

def get_winner(human, bot):
    winner = ''
    if (human == 'rock' and bot == 'paper') or (human == 'scissors' and bot == 'rock') or (human == 'paper' and bot == 'scissors'):
        winner = 'bot'
    elif (human == 'scissors' and bot == 'paper') or (human == 'paper' and bot == 'rock') or (human == 'rock' and bot == 'scissors'):
        winner = 'human'
    elif human == bot:
        winner = 'tie'
    return winner

def display_winner(winner):
    message = ''
    if winner == 'bot':
        message = 'You lost!'
    elif winner == 'human':
        message = 'You won!'
    else:
        message = 'There was a tie!'
    return message

def bot_move(prediction):
    if prediction == 0: # opponent played paper
        bot = 'scissors'
    elif prediction == 1: # opponent played rock
        bot = 'paper'
    elif prediction == 2: # opponent played scissors
        bot = 'rock'
    return bot

def markov_chain(human_moves):
    def window(seq, n=2):
        it = iter(seq)
        result = tuple(islice(it, n))
        if len(result) == n:
            yield result
        for elem in it:
            result = result[1:] + (elem,)
            yield result
    pairs = pd.DataFrame(window(human_moves), columns=['current_throw', 'next_throw'])
    counts = pairs.groupby('current_throw')['next_throw'].value_counts()
    transition_matrix = counts.unstack()
    transition_matrix = transition_matrix.fillna(0)
    transition_matrix['count'] = pairs['current_throw'].value_counts()
    transition_prob = transition_matrix.T / transition_matrix['count']
    transition_prob.drop('count', axis=0, inplace=True)
    return transition_prob

app = flask.Flask(__name__)
bot_type = ''

@app.route('/', methods=['POST', 'GET'])
def home():
    return render_template('home.html')

complete_play = []
human_moves = []
round = []
results = []

@app.route('/smartbot', methods=['POST', 'GET'])
def smartresult():
    game = {}
    bot_type = 'smart bot 🤖'
    if flask.request.method == 'POST':
        player_throw = flask.request.form['player_throw'].split()[0]
        human_moves.append(player_throw)
        if len(round) < 3: # random throw for first two plays
            prediction = np.random.choice([0, 1, 2], p=[1/3, 1/3, 1/3])
        else:
            new_data = pd.DataFrame({'previous_human_throw': [human_moves[len(round)-1]],
                                     'pprevious_human_throw': [human_moves[len(round)-2]],
                                     'previous_winner': [results[len(round)-1]],
                                     'previous_complete_play': [complete_play[len(round)-1]]})
            prediction = smart_bot.predict(new_data)
            markov_chain_predictions = markov_chain(human_moves)
            if len(round) > 10 and len(markov_chain_predictions.index) > 2 and len(markov_chain_predictions.columns) > 2:
                ml_predictions = smart_bot.predict_proba(new_data)
                ml_predictions = {'paper': ml_predictions[0][0], 'rock': ml_predictions[0][1], 'scissors': ml_predictions[0][2]}
                combined_predictions = {}
                combined_predictions[0] = (ml_predictions['paper'] + markov_chain_predictions[player_throw]['paper']) / 2
                combined_predictions[1] = (ml_predictions['rock'] + markov_chain_predictions[player_throw]['rock']) / 2
                combined_predictions[2] = (ml_predictions['scissors'] + markov_chain_predictions[player_throw]['scissors']) / 2
                prediction = [k for k,v in combined_predictions.items() if v == max(combined_predictions.values())][0]
        bot_throw = bot_move(prediction)
        result = get_winner(player_throw, bot_throw)
        results.append(result)
        complete_play.append(bot_throw + '_' + player_throw)
        round.append(1)
        # flask output
        game['result'] = display_winner(result)
        game['player'] = player_throw.capitalize()
        game['bot'] = bot_throw.capitalize()
        tally = Counter(results)
        game['won'] = tally['human']
        game['lost'] = tally['bot']
        if tally['human'] == 0 or tally['bot'] == 0:
            game['win_rate'] = 0
        else:
            game['win_rate'] = int(tally['human'] / (tally['human'] + tally['bot']) * 100)
        game['games_played'] = len(round)
    return render_template('index.html', game=game, bot_type=bot_type)

round_random = []
results_random = []

@app.route('/randombot', methods=['POST', 'GET'])
def randomresult():
    game = {}
    bot_type = 'random bot 💩'
    if flask.request.method == 'POST':
        player_throw = flask.request.form['player_throw'].split()[0]
        bot_throw = np.random.choice(['rock', 'paper', 'scissors'], p=[1/3, 1/3, 1/3])
        result = get_winner(player_throw, bot_throw)
        results_random.append(result)
        round_random.append(1)
        # flask output
        game['result'] = display_winner(result)
        game['player'] = player_throw.capitalize()
        game['bot'] = bot_throw.capitalize()
        tally = Counter(results_random)
        game['won'] = tally['human']
        game['lost'] = tally['bot']
        if tally['human'] == 0 or tally['bot'] == 0:
            game['win_rate'] = 0
        else:
            game['win_rate'] = int(tally['human'] / (tally['human'] + tally['bot']) * 100)
        game['games_played'] = len(round_random)
    return render_template('index2.html', game=game, bot_type=bot_type)

if __name__ == '__main__':
    HOST = '127.0.0.1'
    PORT = 4000
    app.run(HOST, PORT, debug=True)
