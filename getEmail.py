from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
import json
import pymysql

#Connect to mySQL
with open('source\credentials\mysql.json',"r") as f:
    creds = json.load(f)
    _user = creds['sql']['user']
    _pwd = creds['sql']['pwd']
    _host = creds['sql']['host']
    _ip = creds['sql']['ip']
    _db = creds['sql']['db']

conn = pymysql.connect(host=_ip, port=3306, user=_user, passwd=_pwd, db=_db)

def updateMails(data):
    global conn
    #Sql queries
    mailInsert = "INSERT INTO tbl_mail (`mail_id`, `mail_lables`, `mail_snippet`, `mail_to`, `mail_from`,`mail_datetime`,`mail_subject`) "\
                                   " VALUES (%s, %s, %s, %s, %s, %s, %s) "
    tblTruncate = "TRUNCATE tbl_mail"
    cursor = conn.cursor()
    #Truncate everytime to avoid MessageID conflict
    cursor.execute(tblTruncate)
    cursor.executemany(mailInsert,data)
    print(mailInsert)
    conn.commit()
 
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def returnVal(headers,param):
    for header in headers:
        if header['name'] == param:
            return str(header['value'])
            break

def getMsgID(criterias,operand):
    cur = conn.cursor()
    print(criterias)
    #Condition to 
    condition = ''
    for criteria in criterias:
        condition += criteria['header']
        if criteria['filter'] == "contains":
            condition += " LIKE '%"+criteria['value']+"%' "
            if criteria != criterias[-1]:
                condition += " "+operand+" "
            else:
                pass
        elif criteria['filter'] == "does not contains":
            condition += " NOT LIKE '%"+criteria['value']+"%' "
            if criteria != criterias[-1]:
                condition += " "+operand+" "
            else:
                pass
        elif criteria['filter'] == "equals":
            condition += " = '%"+criteria['value']+"%' "
            if criteria != criterias[-1]:
                condition += " "+operand+" "
            else:
                pass
        elif criteria['filter'] == "does not equals":
            condition += " = '%"+criteria['value']+"%' "
            if criteria != criterias[-1]:
                condition += " "+operand+" "
            else:
                pass

    searchQuery = "SELECT mail_id FROM tbl_mail WHERE "+condition
    print(searchQuery)
    cur.execute(searchQuery)
    
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
                'source\credentials\gmail.json', SCOPES)
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

            print(mail)
            #append mail
            mailList.append(mail)

        #updateMails
        updateMails(mailList)

    def criteriaAction(action,messageIds):
        for messageId in messageIds:
            message = service.users().messages().modify(userId='me', id=messageId,
                                                body=action).execute()
            label_ids = message['labelIds']
            
    #import rules
    with open('rules.json') as ruleFile:
        rules = json.load(ruleFile)

        for rule in rules.values():
            if rule['predicate'] == "All":
                operand = "AND"
            elif rule['predicate'] == "Any":
                operand = "OR"
            action = rule['action']
            criteria = rule['criteria']
            messageIds = getMsgID(criteria,operand)
                
            if messageIds != '':
                applyRules = criteriaAction(action,messageIds)
            else:
                print("No Id Found for this criteria")    


if __name__ == '__main__':
    main()