import json
import plotly
import pandas as pd
import re
from sqlalchemy import create_engine

import nltk
import ssl
nltk.download(['stopwords', 'punkt', 'wordnet', 'averaged_perceptron_tagger'])

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

from flask import Flask
from flask import render_template, request, jsonify
from plotly.graph_objs import Bar

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import classification_report
from sklearn.model_selection import GridSearchCV
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier
import joblib


# Initiate Flask.
app = Flask(__name__)


# tokenize takes a text argument and returns a list of tokenized/lemmatized words.
def tokenize(text):
    tokens = word_tokenize(text)
    lemmatizer = WordNetLemmatizer()
    clean_tokens = []
    for tok in tokens:
        clean_tok = lemmatizer.lemmatize(tok)
        clean_tokens.append(clean_tok)
    
    return clean_tokens

# StartingVerbExtractor detects if the first word of the sentence is VB/VBP.
# Return 1 if true and return 0 if false.
class StartingVerbExtractor(BaseEstimator, TransformerMixin):

    def starting_verb(self, text):
        sentence_list = nltk.sent_tokenize(text)
        for sentence in sentence_list:
            pos_tags = nltk.pos_tag(tokenize(sentence))
            first_word, first_tag = pos_tags[0]
            if first_tag in ['VB', 'VBP']:
                return 1
        return 0

    def fit(self, x, y=None):
        return self

    def transform(self, X):
        X_tagged = pd.Series(X).apply(self.starting_verb)
        return pd.DataFrame(X_tagged)


# Load data prepared by process_data.py.
engine = create_engine('sqlite:////home/workspace/models/em_comm.db')
df = pd.read_sql_table('comm', engine)

# Load the ML model preserved by train_classifier.py.
model = joblib.load('/home/workspace/app/em_comm.joblib')


# Index webpage, displays cool visuals, and receives user input text for model.
@app.route('/')
@app.route('/index')
def index():
    
    # Extract data needed for visuals.
    genre_counts = df.groupby('genre').count()['message']
    genre_names = list(genre_counts.index)
    
    df_top = df.iloc[:,3:].sum().sort_values(ascending=False).iloc[0:10]
    top_counts = df_top
    top_cats = list(df_top.index)
    
    
    # Create visuals.
    graphs = [
        {'data': [Bar(x=genre_names, y=genre_counts)],
         'layout': {'title': 'Distribution of Message Genres',
                    'yaxis': {'title': "Count"}, 'xaxis': {'title': "Genre"}}
        },
        {'data': [Bar(x=top_cats, y=top_counts)],
         'layout': {'title': 'Top 10 Most Popular Categories',
                    'yxais': {'title': 'Count'}, 'xaxis': {'title': 'Category'}, 'marker': {'color': 'rgb(200,124,195)'}}
        }
    ]
    
    
    # Encode plotly graphs in JSON.
    ids = ["graph-{}".format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
    
    # render web page with plotly graphs
    return render_template('master.html', ids=ids, graphJSON=graphJSON)


# Web page to handle user query and display model results.
@app.route('/go')
def go():

    # Save user input in query.
    query = request.args.get('query', '') 

    # Use model to predict classification for query.
    classification_labels = model.predict([query])[0]
    classification_results = dict(zip(df.columns[4:], classification_labels))

    # Render the go.html file.
    return render_template(
        'go.html',
        query=query,
        classification_result=classification_results
    )


def main():
    app.run(host='0.0.0.0', port=3001, debug=True)


if __name__ == '__main__':
    main()