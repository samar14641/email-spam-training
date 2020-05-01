import email
import os
import pickle
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from json import dumps
from pprint import pprint


def getLabels():
    labels = os.getcwd() + '\\Data\\full\\index'
    emails = {}  # {'emailID': {'label': int, 'subject': 'str', 'text': 'str'}, ...}, label: 1 --> spam, 0 --> ham 

    with open(labels, 'r') as f:
        line = f.readline()

        while line:
            split = line.strip().split(' ')

            label = 1 if split[0] == 'spam' else 0  # set numeric labels
            key = split[1].split('/')[2]

            emails[key] = {'label': label, 'subject': None, 'text': None}
            # emails[key] = label  # !comment this out if only pickling emails and uncomment line above!

            line = f.readline()

    f.close()

    return emails

def getText(text):
    subject, emailText = '', ''

    msgModel = email.message_from_string(text)  # create msg model
    
    if msgModel['subject'] is not None:
        subject = msgModel['subject']

    if msgModel.is_multipart():
        for current in msgModel.walk():
            extractedText = extract(current)
            emailText += extractedText
    else:
        emailText = extract(msgModel)

    return subject, emailText

def extract(model):
    contentType = model.get_content_type()
    dispo = str(model.get('Content-Disposition'))
    text = ''

    if contentType == 'text/plain' and 'attachment' not in dispo:
        text += model.get_payload()
    elif contentType == 'text/html' and 'attachment' not in dispo:
        html = model.get_payload()
        text += htmlParse(str(html))

    return text

def htmlParse(hmtl):
    parser = BeautifulSoup(hmtl, 'html.parser')
    
    text = parser.getText().strip()
    
    lines = text.split('\n')
    text = ''
    
    for line in lines:  # remove empty lines
        l = line.strip()

        if l != '':
            text += line + '\n'

    return text 

def readFiles():
    emails = getLabels()

    dataPath = os.getcwd() + '\\Data\\data\\'

    files = os.listdir(dataPath)

    count = 1

    for f in files:
        with open(dataPath + f, 'r', encoding = 'ISO-8859-1') as currentFile:
            text = currentFile.read()

            subject, extractedText = getText(text)

            emails[f]['subject'] = subject
            emails[f]['text'] = extractedText

            if count % 100 == 0:
                print(count)

            count += 1

    print(count)

    return emails

def indexing():
    # ES cfg
    indexName = 'emails'
    esCfg = {'host': 'localhost', 'port': 9200}
    es = Elasticsearch(hosts = [esCfg], timeout = 300)

    # delete old index if it exists
    if es.indices.exists(indexName):
        print('deleting old index')
        res = es.indices.delete(indexName)
        print(res)

    # get stoplist
    stoplist = []
    with open(os.getcwd() + '\\Data\\stoplist.txt') as sl:
        sw = sl.readline()

        while sw:
            stoplist.append(sw.strip())
            sw = sl.readline()

    sl.close()

    # index cfg
    requestBody = {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 1,
            'analysis': {
                'filter': {
                    'english_stop': {
                        'type': 'stop',
                        'stopwords': stoplist
                    },
                    'english_stem': {
                        'type': 'stemmer',
                        'language': 'english'
                    }
                },
                'analyzer': {
                    'stopped': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': [
                            'lowercase',
                            'english_stop',
                            'english_stem'
                        ]
                    }
                }
            }
        },
        'mappings': {
            'properties': {
                'text': {
                    'type': 'text',
                    'fielddata': True,
                    'analyzer': 'stopped',
                    'index_options': 'positions'
                }
            }
        }
    }

    print('creating index', indexName)
    res = es.indices.create(index = indexName, body = requestBody)
    print('status:', res)

    print('reading emails')
    emails = readFiles()

    print('indexing')
    count = 1
    bulkData = []

    for e in emails:
        bulkData.append({'index': {'_index': indexName, '_type': '_doc', '_id': e}})
        bulkData.append({'subject': dumps(emails[e]['subject']), 'text': dumps(emails[e]['text']), 'label': emails[e]['label']})

        if count % 50 == 0 or count == len(emails):
            res = es.bulk(index = indexName, body = bulkData)
            bulkData = []
            print(count)

        count += 1
    
    print('*** D O N E ***')

def pcklEmail(emails = None):
    emails = readFiles()

    with open(os.getcwd() + '\\Data\\emailsText.pickle', 'wb') as pckl:
        pickle.dump(emails, pckl, pickle.HIGHEST_PROTOCOL)
    pckl.close()


# pcklEmail()
indexing()