# Smart Door Authentication System on AWS

Project 02 of the Cloud Computing & Big Data Course at NYU taught by Prof. [Sambit Sahu](https://engineering.nyu.edu/sambit-sahu) 

The aim of the project is to implement a distributed authentication system providing access to a virtual door. 

The Authentication & Access system stores new visitor data, provides access to old visitors based on stored data and notifies owner to permit access.

Tools & AWS Services Used: [API Gateway](https://aws.amazon.com/api-gateway/), [DynamoDB](https://aws.amazon.com/dynamodb/), [Kinesis](https://aws.amazon.com/kinesis/), [Lambda](https://aws.amazon.com/lambda/), [Rekognition](https://aws.amazon.com/rekognition/), [S3](https://aws.amazon.com/s3/), [SNS](https://aws.amazon.com/sns/), [Postman](https://www.postman.com/)  


## System Architecture & Workflow

<p align="center">
  <img src="https://github.com/Dhuldhoyavarun/smart_door_authentication_system/blob/main/Lambda_functions/Architecture.PNG" width='700' title="Architecture">
</p>

+ The S3 bucket B1 is used to store images. Bucket B2 stores front-end webpages WP1 & WP2.  
WP1 is used to take visitor details such as the name and phone number of visitor.  
WP2 acts as a virtual door that prompts the user to input OTP.

+ DynamoDB database table DB1 stores temporary access codes to the door and a reference to the visitor it was assigned to. Using the TTL feature, all records expire after 5 mins.  
Table DB2 stores details of visitors processed using Rekognition. Each FaceId detected by Rekognition is indexed and stored in DB2 alongside the name of the vistor and their phone number.  
If a FaceId already exists for a visitor, the new photo is appended to the existing visitor's photo array.

+ The Kinesis Video Stream captures video stream from the webcam set up on a local computer. The Rekognition Video service is subscribed to the Kinesis Video Stream. The output of the Rekognition service is sent to Kinesis Data Stream for further processing.  

+ The Rekognition service outputs lead to two scenarios:  
  + For every known face detected, a lambda function is triggered which sends an SMS to the recognised person's phone number containing an OTP that is used to open the virtual door.  
  + For every unknown face detected, an Email is sent to the administrator containing a photo of the visitor and a link to the approval form(WP1). The details entered in the approval form are used to create a new record in DB2 with the FaceId indexed by the Rekognition service. An OTP is sent to new visitor with a set expiration time of 5 minutes.  

