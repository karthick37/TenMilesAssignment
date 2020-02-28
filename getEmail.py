from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import mysql.connector
from mysql.connector import Error
import base64
import json
import pymysql

#Connect to mySQL
with open('mySQL_creds.json') as f:
    sqlCreds = json.load(f)
    mySqlUser = sqlCreds['mySqlAdmin']['user']
    mySqlPwd = sqlCreds['mySqlAdmin']['pwd']
    mySqlHost = sqlCreds['mySqlAdmin']['host']
    mySqlHostIp = sqlCreds['mySqlAdmin']['hostIP']
    mySqlDB = sqlCreds['mySqlAdmin']['db']

connection = mysql.connector.connect(user=mySqlUser, password=mySqlPwd,
                                    host=mySqlHost,
                                    database=mySqlDB)
def insertRows(data):
    # take creds from json 
    
    insertQuery = "INSERT INTO tbl_mail (`mail_id`, `mail_lables`, `mail_snippet`, `mail_to`, `mail_from`,`mail_datetime`,`mail_subject`) "\
                                   " VALUES (%s, %s, %s, %s, %s, %s, %s) "
    truncate = "TRUNCATE tbl_mail"
    try:
        global connection
        cursor = connection.cursor()

        #Truncate everytime to avoid MessageID conflict
        cursor.execute(truncate)
        cursor.executemany(insertQuery,data)
        print(insertQuery)
        connection.commit()
    except mysql.connector.Error as error:
        print("Failed to insert into MySQL table {}".format(error))
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
        else:
            print('not connected')
 
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def returnVal(headers,param):
    for header in headers:
        if header['name'] == param:
            return str(header['value'])
            break

def getMsgID(header,filter,value):

    #mysql connector having some issues with Select Queries. Using a diff package for select querirs
    conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='', db='db_gmail')
    cur = conn.cursor()

    if filter == "contains":
        searchQuery = "SELECT mail_id FROM tbl_mail WHERE mail_from LIKE %s"
        cur.execute(searchQuery,"%"+value+"%")
    if filter == "does not contains":
        searchQuery = "SELECT mail_id FROM tbl_mail WHERE mail_from NOT LIKE %s"
        cur.execute(searchQuery,"%"+value+"%")
    if filter == "equals":
        searchQuery = "SELECT mail_id FROM tbl_mail WHERE mail_from = %s"
        cur.execute(searchQuery,value)
    if filter == "does not equals":
        searchQuery = "SELECT mail_id FROM tbl_mail WHERE %s != %s"
        cur.execute(searchQuery,value)
    
    ids = []
    for row in cur:
        ids.append(row[0])

    cur.close()
    conn.close()

    return ids

def main():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    msgCount = int(input("Max Email : "))

    # Call the Gmail API
    results = service.users().messages().list(userId='me',labelIds=['INBOX'],q="is:unread",maxResults=msgCount).execute()
    messages = results.get('messages', [])
    
    mailList = []

    if not messages:
        print('No mails found')
    else:
        i = 1
        for message in messages:
            mail = []
            #Get Message Details
            msg = service.users().messages().get(userId='me', id=message['id']).execute()

            #fetching values for DB
            msgId = str(msg['id'])
            mail.append(msgId)

            lables = ','.join(msg['labelIds'])
            mail.append(lables)
            
            headers = msg['payload']['headers']
            
            snippet = str(msg['snippet'])
            mail.append(snippet)
            
            toMail = returnVal(headers,"Delivered-To")
            mail.append(toMail)

            fromMail = returnVal(headers,"From")
            mail.append(fromMail)
            
            Date = returnVal(headers,"Date")
            mail.append(Date)

            subjectMail = returnVal(headers,"Subject")
            mail.append(subjectMail)

            # body = msg['body']['data']
            # decodedmsg = base64.b64decode(body)
            # rawMsgStr = str(decodedmsg, "utf-8")

            print(mail)
            #append mail
            mailList.append(mail)

        #insertRows
        # mailList = tuple(i for i in mailList)
        insertRows(mailList)

    def criteriaAction(action,messageIds):
        for messageId in messageIds:
            print(messageIds)

    #Play with sql data
    #import rules
    with open('rules.json') as ruleFile:
        rules = json.load(ruleFile)

        for rule in rules.values():
            if rule['predicate'] == "All":
                action = rule['action']
                for criteria in rule['criteria']:                    
                    header = criteria['header']
                    value = criteria['value']
                    filter = criteria['filter']
                    messageIds = getMsgID(header,filter,value)
                    
                    if messageIds != '':
                        TakeAction = criteriaAction(action,messageIds)
                    else:
                        print("No Id Found for this criteria")    


if __name__ == '__main__':
    main()