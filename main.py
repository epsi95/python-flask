# install the libraries
# python -m pip install Flask
# python -m pip install ibm-cos-sdk


# importing standard libraries
import os
import math

# importing flask
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename

# importing ibm boto3 library
import ibm_boto3
from ibm_botocore.client import Config, ClientError

# allowed extension of uplodable file, zip is preferred
ALLOWED_EXTENSIONS = set(['zip'])


# Constants for IBM COS values
COS_ENDPOINT = "<endpoint>" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "<api-key>" # eg "W00YiRnLW4a3fTjMB-oiB-2ySfTrFBIQQWanc--P3byk"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN = "<resource-instance-id>" #eg "crn:v1:bluemix:public:cloud-object-storage:global:a/3bf0d9003abfb5d29761c3e97696b71c:d6f04d83-6c4f-4a62-a165-696756d63903::"

''' 
<endpoint> - public endpoint for your cloud Object Storage with schema prefixed ('https://') (available from the IBM Cloud Dashboard). For more information about endpoints, see Endpoints and storage locations.
<api-key> - api key generated when creating the service credentials (write access is required for creation and deletion examples)
<resource-instance-id> - resource ID for your cloud Object Storage (available through IBM Cloud CLI or IBM Cloud Dashboard)

To generate this credentials: goto objectstorage --> Service credentials --> New Credentials --> get <api-key>,<resource-instance-id> from here
For <endpoint> create new `bucket`, then select configure --> Public Endpoint --> select the link
<endpoint> = 'https://' + link
'''

# creating flask object
app = Flask(__name__)


# function to upload the file (here file is uploaded in chunks of 5MB if file_size > 5MB
def multi_part_upload_manual(bucket_name, item_name, file, length):
        try:
            # create client object
            cos_cli = ibm_boto3.client("s3",
                ibm_api_key_id=COS_API_KEY_ID,
                ibm_service_instance_id=COS_RESOURCE_CRN,
                ibm_auth_endpoint=COS_AUTH_ENDPOINT,
                config=Config(signature_version="oauth"),
                endpoint_url=COS_ENDPOINT
            )

            print("Starting multi-part upload for {0} to bucket: {1}\n".format(item_name, bucket_name))

            # initiate the multi-part upload
            mp = cos_cli.create_multipart_upload(
                Bucket=bucket_name,
                Key=item_name
            )

            upload_id = mp["UploadId"]

            # min 5MB part size
            part_size = 1024 * 1024 * 5
            file_size = length
            #print(file_size)
            part_count = int(math.ceil(file_size / float(part_size)))
            data_packs = []
            position = 0
            part_num = 0
            ind = 0

            # begin uploading the parts
            #with open(file_path, "rb") as f:
            for i in range(part_count):
                part_num = i + 1
                part_size = min(part_size, (file_size - position))
                #print("partsize", part_size)

                print("Uploading to {0} (part {1} of {2})".format(item_name, part_num, part_count))

                file_data = file.read(part_size)
                #print(type(file_data))
                #print(len(file_data))

                mp_part = cos_cli.upload_part(
                    Bucket=bucket_name,
                    Key=item_name,
                    PartNumber=part_num,
                    Body=file_data,
                    ContentLength=part_size,
                    UploadId=upload_id
                )

                data_packs.append({
                    "ETag":mp_part["ETag"],
                    "PartNumber":part_num
                })

                position += part_size

            # complete upload
            cos_cli.complete_multipart_upload(
                Bucket=bucket_name,
                Key=item_name,
                UploadId=upload_id,
                MultipartUpload={
                    "Parts": data_packs
                }
            )
            print("Upload for {0} Complete!\n".format(item_name))
        except ClientError as be:
            # abort the upload
            cos_cli.abort_multipart_upload(
                Bucket=bucket_name,
                Key=item_name,
                UploadId=upload_id
            )
            print("Multi-part upload aborted for {0}\n".format(item_name))
            print("CLIENT ERROR: {0}\n".format(be))
        except Exception as e:
            print("Unable to complete multi-part upload: {0}".format(e))





# method to check allowed filename
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# define route
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect("No file part")


        file = request.files['file']

        file.seek(0, os.SEEK_END)
        size = file.tell()
        #seek to its beginning, so you might save it entirely
        file.seek(0)
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect("No file selected")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            multi_part_upload_manual("xxxx", filename, file, size) # xxxx is your bucket name
            # file upload successful, return successful message
            return ('''
                      <!doctype html>
                      <title>Upload new File</title>
                      <h1>Upload successful</h1>
                      ''')
    else: # GET request
      return '''
      <!doctype html>
      <html>
        <head>
          <title>Upload new File</title>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>

          .loader {
            border: 16px solid #f3f3f3;
            border-radius: 50%;
            border-top: 16px solid #3498db;
            width: 120px;
            height: 120px;
            -webkit-animation: spin 2s linear infinite; /* Safari */
            animation: spin 2s linear infinite;
            opacity: 100
                  }

          /* Safari */
          @-webkit-keyframes spin {
            0% { -webkit-transform: rotate(0deg); }
            100% { -webkit-transform: rotate(360deg); }
                 }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
                 }

          body {font-family: Arial, Helvetica, sans-serif;}

           /* The Modal (background) */
          .modal {
            display: none; /* Hidden by default */
            position: fixed; /* Stay in place */
            z-index: 1; /* Sit on top */
            padding-top: 100px; /* Location of the box */
            left: 0;
            top: 0;
            width: 100%; /* Full width */
            height: 100%; /* Full height */
            overflow: auto; /* Enable scroll if needed */
            background-color: rgb(0,0,0); /* Fallback color */
            background-color: rgba(0,0,0,0.4); /* Black w/ opacity */
                 }

          /* Modal Content */
          .modal-content {
            background-color: rgba(0, 0, 0, 0);
            margin: auto;
            padding: 10px;
            width: 23%;
                }

          /* The Close Button */
          .close {
            color: #aaaaaa;
            float: right;
            font-size: 0px;
            font-weight: bold;
            opacity: 0
                }

          .close:hover,
          .close:focus {
            color: #000;
            text-decoration: none;
            cursor: pointer;
                }
          </style>
        </head>
        <body>

        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
          <input type=file name=file>
          <input type=submit value=Upload onclick = myfunction()>
        </form>

        <!-- The Modal -->
        <div id="myModal" class="modal">

          <!-- Modal content -->
          <div class="modal-content">
            <span class="close">&times;</span>
            <div class="loader"></div>
          </div>

        </div>

        <script>
        // Get the modal
        var modal = document.getElementById("myModal");


        // When the user clicks on <span> (x), close the modal
        span.onclick = function() {
          modal.style.display = "none";
        }

        // When the user clicks anywhere outside of the modal, close it
        window.onclick = function(event) {
          if (event.target == modal) {
            modal.style.display = "none";
          }
        }

        function myfunction(){
        modal.style.display = "block";
        }
        </script>

        </body>
      </html>
      '''






