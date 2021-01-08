import json
import logging
import boto3
from datetime import datetime
from datetime import timedelta
import random
logger = logging.getLogger()
logger.setLevel(logging.INFO) 

def sendSMS(phone,faceId,otp):
    sns = boto3.client('sns', region_name = 'us-west-2')
    url = "https://smart-door-face.s3-us-west-2.amazonaws.com/OTPlogin.html?faceId="+faceId
    message = "Your OTP is - " + str(otp) + "\n\n Click here to enter OTP " + url
    print(message)
    try:
        res = sns.publish(
            PhoneNumber = '+1' + phone,
            Message = message,
            MessageStructure = 'string'
            )
    except KeyError:
        print("error in sending sms")
        
        
def generateOTP():
    return random.randint(1000,9999)    


def putToDynamoDbPasscodes(table, faceId):
    epochafter5 = int(datetime.now().timestamp()) + 300
    otp = generateOTP()
    table.put_item(
        Item={
            'faceId' : faceId,
            'expirationtimestamp' : epochafter5,
            'currenttimestamp' : (epochafter5 - 300),
            'OTP' :otp
            })
    return otp    
    

def getTimeStamp(fileName):
    s3 = boto3.client('s3')
    print(fileName)
    response = s3.get_object(
        Bucket = 'smart-door-face',
        Key = fileName
    )
    return response['LastModified'].strftime("%Y-%m-%d %H:%M:%S")
    

def putToDynamoDbVisitors(table,faceId,name,phone,fileName):
    table.put_item(
        Item={
            'faceId': faceId,
            'name': name,
            'phone': phone,
            'photos': {
                'objectKey' : fileName,
                'bucket' : "smart-door-face",
                'createdTimestamp' : getTimeStamp(fileName)
                },
            'account_type': 'standard_user',
        }
    )
    

def connectToDB(tableName):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(tableName)
    print(table.creation_date_time)
    return table
   

def extractInformation(event):
    request = event["message"]
    #faceId = request["faceId"]
    name = request["name"]
    phone = request["phone"]
    fileName = request["fileName"]
    return name, phone, fileName


def indexFaceRekognition(buffer,name):
    rek = boto3.client('rekognition')
    res = rek.index_faces(
    CollectionId = 'smartdoor-visitors',
     Image={
        'Bytes' : buffer
        },
    ExternalImageId = name
    )
    return res


def getFaceId(fileName,name):
    #bt3 = boto3.session.Session(aws_access_key_id='', aws_secret_access_key='',region_name='us-west-2')
    s3 = boto3.client('s3')
    res = s3.get_object(
        Bucket = 'smart-door-face',
        Key = fileName
    )
    data = res['Body'].read()
    res = indexFaceRekognition(data,name)
    return res['FaceRecords'][0]['Face']['FaceId']

    
def lambda_handler(event, context):
    name, phone, fileName = extractInformation(event)
    print(name,phone,fileName)
    logger.info(fileName)
    faceId = getFaceId(fileName, name)
    print("faceid=",faceId)
    table = connectToDB('visitors')
    putToDynamoDbVisitors(table,faceId,name,phone,fileName)
    table = connectToDB('passcodes')
    otp = putToDynamoDbPasscodes(table,faceId)
    sendSMS(phone,faceId,otp)
    message = "Thank you, visitor added to database"
    return {
        'statusCode': 200,
        'body': message
    }
