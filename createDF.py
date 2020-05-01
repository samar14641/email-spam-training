import elasticsearch
import os
import pandas as pd
import pickle
from pprint import pprint


def readPckl(fileName):
    obj = {}

    with open(fileName, 'rb') as pckl:
        obj = pickle.load(pckl)

    pckl.close()

    return obj

def esCfg():
    indexName = 'emails'
    esCFG = {'host': 'localhost', 'port': 9200}
    es = elasticsearch.Elasticsearch(hosts = [esCFG], timeout = 600000)

    return es, indexName

def esAnalyse(es, indexName):  # stop and stem features
    rawFeatures = set(('free', 'spam', 'click', 'buy', 'clearance', 'shopper', 'order', 'earn', 'cash', 'extra', 'money', 'double', 'collect', 'credit', 'check', 'affordable', 'fast', 'price', 'loans', 'profit', 'refinance', 'hidden', 'freedom', 'chance', 'miracle', 'lose', 'home', 'remove', 'success', 'virus', 'malware', 'ad', 'subscribe', 'sales', 'performance', 'viagra', 'valium', 'medicine', 'diagnostics', 'million', 'join', 'deal', 'unsolicited', 'trial', 'prize', 'now', 'legal', 'bonus', 'limited', 'instant', 'luxury', 'legal', 'celebrity', 'only', 'compare', 'win', 'viagra', 'click', 'here', 'meet', 'singles', 'incredible', 'deal', 'lose', 'weight', 'act', 'now', 'free', 'fast', 'cash', 'million', 'dollars', 'lower', 'interest', 'rate', 'visit', 'our', 'website', 'no', 'credit', 'check'))
    features = []

    analyse = {
        'analyzer': 'stopped',
        'text': list(rawFeatures)
    }
    res = es.indices.analyze(index = indexName, body = analyse)

    for tokenData in res['tokens']:
        features.append(tokenData['token'])

    pickleFeat = True
    if pickleFeat:
        with open(os.getcwd() + '\\Data\\featList.pickle', 'wb') as pckl:
            pickle.dump(features, pckl, pickle.HIGHEST_PROTOCOL)
        pckl.close()

    return features

def main():
    es, indexName = esCfg()

    features = esAnalyse(es, indexName)  # get stopped and stemmed features

    emails = readPckl(os.getcwd() + '\\Data\\emails.pickle')

    allData = {i: {f: 0 for f in features} for i in emails}
    for i in allData:
        allData[i]['label'] = emails[i]

    tvReq = {
            'fields': ['text'],
            'term_statistics': False,
            'field_statistics': False
        }

    # get tf data
    for email in emails:
        res = es.termvectors(index = indexName, body = tvReq, id = email)

        print(email)

        if 'text' in res['term_vectors']:
            tokens = res['term_vectors']['text']['terms']

            for f in features:
                if f in tokens:
                    allData[email][f] = tokens[f]['term_freq']

    df = pd.DataFrame.from_dict(allData, orient = 'index')  # create df

    pprint(df.head())
    print(df.shape)

    df.to_pickle(os.getcwd() + '\\Data\\features.pkl')


main()