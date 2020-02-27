from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import mysql.connector
from mysql.connector import Error

def insertRows(msgId,lables,to,from_,subject,snippet,datetime):
    print(msgId)
    try:
        connection = mysql.connector.connect(user='root', password='',
                                    host='127.0.0.1',
                                    database='db_gmail')
        cursor = connection.cursor()
        insertQuery = """INSERT INTO tbl_mail (mail_id, mail_lables, mail_to, mail_from,mail_subject,mail_snippet,mail_datetime) 
                                    VALUES ('msgId',lables,to,from_,subject,snippet,datetime) """
        connection.commit()
        print(insertQuery)
    except mysql.connector.Error as error:
        print("Failed to insert into MySQL table {}".format(error))
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
 
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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
    
    if not messages:
        print('No mails found')
    else:
        i = 1
        for message in messages:
            #Get Message Details
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            #fetching values for DB
            print(msg)
            lables = msg['labelIds']
            msgId = msg['id']
            headers = msg['payload']['headers']
            snippet = msg['snippet']
            for header in headers:
                if header['name'] == "Delivered-To":
                    toMail = header['value']
                else:
                    toMail = ""
                if header['name'] ==  "From":
                    fromMail = header['value']
                    print(fromMail)
                else:
                    fromMail = ""
                if header['name'] == "Subject":
                    subjectMail = header['value']
                else:
                    subjectMail = ""
                if header['name'] == "Date":
                    dateMail = header = header['value']
                else:
                    dateMail = ""

            #insertRows
            if(insertRows(msgId,lables,toMail,fromMail,subjectMail,snippet,dateMail)):
                print(i,' row inserted')



if __name__ == '__main__':
    main()