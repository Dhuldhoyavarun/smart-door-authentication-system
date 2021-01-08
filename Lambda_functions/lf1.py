from __future__ import print_function

import json

import base64
import boto3
import logging
import random
import uuid
import cv2
from datetime import datetime
from os import listdir
logger = logging.getLogger()
logger.setLevel(logging.INFO) 

def sendSMS(faceId, phone, otp):
    sns = boto3.client('sns',region_name= 'us-west-2')
    url = "https://smart-door-face.s3-us-west-2.amazonaws.com/OTPlogin.html?faceId="+faceId
    message = "Your OTP is - " + str(otp) + "\n\n click here to enter OTP " + url
    print(message)
    try:
        res = sns.publish(
            PhoneNumber = '+1'+ phone,
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


def getVisitorsPhoneNumber(tableName,faceId):
    print("get_visitor_phone_number")
    item = tableName.get_item( 
        Key={'faceId': faceId
        })
    return item['Item']['phone']
    
    
def connectToDB(tableName):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(tableName)
    print(table.creation_date_time)
    return table  


def sendEmail(url,fileName):
    visitorUrl = "https://smart-door-face.s3-us-west-2.amazonaws.com/VisitorInfo.html?fileName="+fileName
    ses = boto3.client('ses')
    response = ses.send_email(	Destination={
        'ToAddresses': [
            'mcp573@nyu.edu',
            'vyd208@nyu.edu',
            ],
    },
    Message={
        'Body': {
            'Html': {
                'Charset': 'UTF-8',
                'Data': '<a class="ulink" href="'+url+'">Click here for Vistors photo</a>.<br><br>'+
                    '<a class= "ulink" href = "'+visitorUrl+'">Click here to enter the Visitor Information</a>',
            }
        },
        'Subject': {
            'Charset': 'UTF-8',
            'Data': 'SmartDoor Email Lambda Function',
        },
    },
    Source='vydhuldhoya@gmail.com' 
    )


def countNumberOfFrames(vidcap,fileName):
    total = 0
    while True:
        success, image = vidcap.read()
        if not success:
            break
        total+=1
        if total > 500:
            break
    vidcap.release()
    vidcap.open(fileName)
    for i in range(1,int(total/2)):
        success, image = vidcap.read()
    return success,image


def getEndpoint(streamName):
    kvm = boto3.client("kinesisvideo")
    endpt = kvm.get_data_endpoint( 
        APIName = "GET_MEDIA_FOR_FRAGMENT_LIST",
        StreamName=streamName,
    )
    return endpt["DataEndpoint"]
    
def getImageFromFragments(endpoint, streamName, fragmentNumber):
    kvm = boto3.client('kinesis-video-archived-media',endpoint_url = endpoint)  
    response = kvm.get_media_for_fragment_list(
        StreamName=streamName,
        Fragments=[
            fragmentNumber,
        ]
    )
    print("FragmentNumber: "+fragmentNumber)
    
    mkvFileName = '/tmp/test.mkv'
    jpgFileName = '/tmp/frame.jpg'
    stream = response["Payload"]
    f = open(mkvFileName,'wb')
    f.write(stream.read())
    f.close()
    
    vidcap = cv2.VideoCapture(mkvFileName) 
    success,image = countNumberOfFrames(vidcap,mkvFileName)
    if success:
        cv2.imwrite(jpgFileName , image) 
    
    return jpgFileName

def uploadFileToS3Bucket(bucket, jpgFileName, identifier):
 
    s3_client = boto3.client('s3')
    s3_client.upload_file(
        jpgFileName,    
        bucket,         
        'frame_{}.jpeg'.format(identifier),   
         ExtraArgs={'GrantFullControl': 'uri="http://acs.amazonaws.com/groups/global/AllUsers"'} 
    )


def getEmailDetails(bucket,identifier):
    fileName = "frame_"+identifier+".jpeg"
    url = "https://"+bucket+".s3.amazonaws.com/"+fileName
    return url,fileName


def getParametersFromKDS(event):
    for record in event['Records']:
 
        payload=base64.b64decode(record["kinesis"]["data"])
        print("Decoded payload: " + str(payload))
    
        json_data = json.loads(payload.decode('utf-8'))
        # print("Decoded json_data payload: " + str(json_data))
        face_search_response = json_data['FaceSearchResponse']
        
        
        
        if face_search_response:
            # return ("No one at the door")
            for faces in face_search_response:
                if faces['MatchedFaces']:
                    faceId = faces['MatchedFaces'][0]['Face']['FaceId']
                    print('FACEID ',faceId)
                    return True, faceId , None
                else:
                    fragmentNumber= json_data['InputInformation']['KinesisVideo']['FragmentNumber']
                    return True, None, fragmentNumber
        else:
            
            return False,None,None
            
def checkForDuplicates(passcodetable,faceId):
    
    try: 
        dynamodb = boto3.client('dynamodb')
        res = dynamodb.get_item(
            TableName = "passcodes",
            Key = {
                'faceId' : {
                    'S' : faceId
                }
            })
        timeStamp = res["Item"]["expirationtimestamp"]["N"]
        curTimeStamp = int(datetime.now().timestamp())
        return curTimeStamp <= int(timeStamp)
    except KeyError:
        return False

def checkEmailDuplicate(emailTable, ownerEmailId):
    try:
        dynamodb = boto3.client('dynamodb')
        res = dynamodb.get_item(
            TableName = "emails",
            Key = {
                'emailId' : {
                    'S' : ownerEmailId
                }
            })
            
        timeStamp = res["Item"]["expirationtimestamp"]["N"]
        curTimeStamp = int(datetime.now().timestamp())
        return curTimeStamp <= int(timeStamp)
    except KeyError:
        return False
        
    
def putToDynamoDbEmailFilter(table, ownerEmailId):
    currenttimestamp = int(datetime.now().timestamp()) 
    table.put_item(
        Item={
            'emailId' : ownerEmailId,
            'expirationtimestamp' : (currenttimestamp + 300),
            'currenttimestamp' : currenttimestamp,
            })
    print("Added email to the email filter");
    return True
    
    
def lambda_handler(event, context):
    print(event)
    print(listdir("/opt/build/python/lib/python3.8/site-packages"))
    

    success, faceId, fragmentNumber = getParametersFromKDS(event)  
    
  
    
    if success:
        if faceId is not None: 
            print("Valid Vistor")
            passcodetable = connectToDB("passcodes")
            if not checkForDuplicates(passcodetable,faceId):
                otp = putToDynamoDbPasscodes(passcodetable,faceId)
                vistiorsTable = connectToDB("visitors")
                phoneNumber = getVisitorsPhoneNumber(vistiorsTable,faceId)
                print("phone "+ phoneNumber)
                sendSMS(faceId, phoneNumber, otp)
            else:
                print("Duplicate Request for FaceId - " + faceId)
        
        elif fragmentNumber is not None: 
            print("Unknown Vistor")
            streamName="smart-door"
            bucket = "smart-door-face"
            identifier=str(uuid.uuid1())
            emailTable = connectToDB("emails")
            print("uuid "+identifier)
            ownerEmailId = "vyd208@nyu.edu"
            if not checkEmailDuplicate(emailTable, ownerEmailId):
                endpoint = getEndpoint(streamName)
                jpgFileName = getImageFromFragments(endpoint, streamName, fragmentNumber)
                url, fileName = getEmailDetails(bucket, identifier)
                uploadFileToS3Bucket(bucket, jpgFileName, identifier)
                print("Send Email")
                # add data in emailfilter table
                putToDynamoDbEmailFilter(emailTable,ownerEmailId)
                sendEmail(url, fileName)
            else:
                print("Duplicate Email Request")
    else:
        print("No one at the Door")
        return ("No one at the Door")
        
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
