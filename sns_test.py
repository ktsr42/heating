import boto3

def main():
    session = boto3.Session(profile_name = 'root')
    sns = session.client('sns')
    sns.publish(PhoneNumber='+15515802081', Message='Hello again from folio')

if __name__ == '__main__':
    main()
