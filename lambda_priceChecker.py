# the function will check the price by the product and compare it with the desired price.
from __future__ import print_function
import json, urllib.parse, boto3, datetime, requests
from boto3.dynamodb.conditions import Key
from bs4 import BeautifulSoup

# Connect to S3 and DynamoDB
dynamodb = boto3.resource('dynamodb')
# Connect to the DynamoDB tables
ProductTable     = dynamodb.Table('Product');
ProductPriceTable     = dynamodb.Table('ProductPrice');

# Connect to SNS
sns = boto3.client('sns')
alertTopic = 'LowerPriceAlert'
snsTopicArn = [t['TopicArn'] for t in sns.list_topics()['Topics'] if t['TopicArn'].endswith(':' + alertTopic)][0]


def return_NameandPrice(linkstring):
    header={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.67 Safari/537.36 Edg/87.0.664.47'}
    page = requests.get(linkstring,headers=header)
    content = BeautifulSoup(page.content, 'html.parser')
    #deal = content.select('.ebayui-dne-item-featured-card--topDeals')[0]
    #item = top_deal.select('.dne-itemtile-title')[0].get_text()
    product_Price = int(float(content.find(id='priceblock_ourprice').text[1:]))
    product_Name = content.find(id='productTitle').text.strip()
    #print(product_Name)
    #print(product_Price)
    dict={'Time':str(datetime.datetime.now()),'Name':product_Name, 'Price':product_Price}
    return dict

# This handler is executed every time the Lambda function is triggered
def lambda_handler(event, context):

  # Show the incoming event in the debug log
    print("Event received by Lambda function: " + json.dumps(event, indent=2))
  # Read the Transactions CSV file. Delimiter is the '|' character

    ProductItems = ProductTable.scan()['Items']
    productNo = len(ProductItems)
    #print(productNo)
    if productNo>0:
        for myitem in ProductItems:
            try:
                product_ID= myitem['ProductID']
                target_Price= myitem['TargetPrice']
                product_Link= myitem['ProductLink']
                #print(product_ID)
                #print(target_Price)
                
                mydata = return_NameandPrice(product_Link)
                

                ProductPriceTable.put_item(
                    Item={
                        'ProductID': product_ID,
                        'LastUpdateTime':mydata['Time'],
                        'ProductPrice':mydata['Price'],
                        'ProductName': mydata['Name'] })
                        
                if mydata['Price']<target_Price:
                    # Send message to SNS
                    # Construct message to be sent
                    message = 'The Amazon product: "' + mydata['Name'] + '"' + 'comes to a lower price: "£' + str(mydata['Price']) + '".'
                    sns.publish(
                        TopicArn=snsTopicArn,
                        Message=message,
                        Subject='Lower Price founded for the product in your wishlist',
                        MessageStructure='raw'
                        )
                
    
            except Exception as e:
                print(e)
                print("Unable to insert data into DynamoDB table".format(e))

    # Finished!
    return ("Lambda finished")
