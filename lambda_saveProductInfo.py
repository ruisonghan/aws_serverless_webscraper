# Name of the lambda function: lambda_saveProductInfo
# Running environment: python 3.8
# This function is triggered by a .txt file being uploaded in an Amazon S3 bucket. The file will be downloaded by the fucntion and each line is inserted into DynamoDB tables.
# Besides, it will use the bs4 and requests to get the initial price of products and save them to DynamoDB tables.

from __future__ import print_function
import json, urllib.parse, boto3, csv, datetime, requests, base64
from bs4 import BeautifulSoup

# Connect to S3 and DynamoDB
s3 = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')

# Connect to the DynamoDB tables
ProductTable     = dynamodb.Table('Product');
ProductPriceTable     = dynamodb.Table('ProductPrice');

# Check the price of a product using its web link. bs4 and request libraries are used here to get the price info from the web page.
def return_NameandPrice(linkstring):
    header={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.67 Safari/537.36 Edg/87.0.664.47'}
    page = requests.get(linkstring,headers=header)
    content = BeautifulSoup(page.content, 'html.parser')
    #deal = content.select('.ebayui-dne-item-featured-card--topDeals')[0]
    #item = top_deal.select('.dne-itemtile-title')[0].get_text()
    product_Price = int(float(content.find(id='priceblock_ourprice').text[1:]))
    product_Name = content.find(id='productTitle').text.strip()
    product_ImgLink= content.find(id='imgTagWrapperId').img.get('src')
    #print(product_Name)
    #print(product_Price)
    dict={'Time':str(datetime.datetime.now()),'Name':product_Name, 'Price':product_Price, "Image":product_ImgLink}
    return dict

# This handler is executed every time the Lambda function is triggered
def lambda_handler(event, context):
  # Show the incoming event in the debug log
  print("Event received by Lambda function: " + json.dumps(event, indent=2))

  # Get the bucket and object key from the Event
  bucket = event['Records'][0]['s3']['bucket']['name']
  key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
  # save the txt file as a local file which can read by other packages further.
  localFilename = '/tmp/pricehistory.txt'

  # Download the file from S3 to the local filesystem
  try:
    s3.meta.client.download_file(bucket, key, localFilename)
  except Exception as e:
    print(e)
    print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
    raise e

  # Read the Transactions CSV file. Delimiter is the '|' character
  with open(localFilename) as csvfile:
    reader = csv.DictReader(csvfile, delimiter='|')

    # Read each row in the file
    rowCount = 0
    for row in reader:
      rowCount += 1
      # Show the row in the debug log
      print(row['product_ID'], row['target_Price'])

      try:
        # Insert Product ID and Address into Product (info) DynamoDB table
        weblink='https://www.amazon.co.uk/gp/product/'+ row['product_ID']+ '/'
        ProductTable.put_item(
          Item={
            'ProductID': row['product_ID'],
            'TargetPrice': int(row['target_Price']),
            'ProductLink': weblink})
        
        mydata = return_NameandPrice(weblink)    
        # decode the product image in the html and save it.
        imgdata = base64.b64decode(mydata['Image'].replace('data:image/jpeg;base64,',''))
        filename = '/tmp/productImage.jpg'  # I assume you have a way of picking unique filenames
        with open(filename, 'wb') as f:
          f.write(imgdata)
          f.close()
        # return the product image to S3
        response = s3.meta.client.upload_file(filename, bucket, 'img/'+ row['product_ID']+'.jpg')
        
        # insert product info into the ProductPrice table.
        ProductPriceTable.put_item(
          Item={
            'ProductID': row['product_ID'],
            'LastUpdateTime':mydata['Time'],
            'ProductPrice':mydata['Price'],
            'ProductName': mydata['Name']
            
          })

      except Exception as e:
         print(e)
         print("Unable to insert data into DynamoDB table".format(e))

    # Finished!
    return ("%d transactions inserted" % rowCount)
