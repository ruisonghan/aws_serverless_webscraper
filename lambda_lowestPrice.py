# the function will return the lowest price of an Amazon product, if that product is in our DB.
import json, boto3
from boto3.dynamodb.conditions import Key

# Connect to S3 and DynamoDB
dynamodb = boto3.resource('dynamodb')
# Connect to the DynamoDB tables
ProductPriceTable     = dynamodb.Table('ProductPrice');

class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                return float(o)
            super(DecimalEncoder, self).default(o)

# the handler is trigger by API and will search the lowest price of a product in DB
def lambda_handler(event, context):

    # Show the incoming event in the debug log
    print("Event received by Lambda function: " + json.dumps(event, indent=2))
    event = json.loads(event.get('body'))

    ProductID=event['ProductID']
    try:
        myresults=ProductPriceTable.query(KeyConditionExpression=Key('ProductID').eq(ProductID))['Items']
        lowestPrice=10000000000
        date4Lowest=""
        if len(myresults)>0:
            for myitem in myresults:
                if myitem["ProductPrice"]<lowestPrice:
                    lowestPrice = myitem["ProductPrice"];
                    date4Lowest = myitem["LastUpdateTime"]
                
            mydict={"LowestPrice":int(lowestPrice),"Date":date4Lowest}
 
            return {
                'statusCode':200,
                'body': json.dumps(mydict)
                }
                
        else:
            return {
            'statusCode':201,
            'body':json.dumps('The product does not exist in our database.')
            }
            
    except Exception as e:
        print(e)
        return {
            'statusCode':400,
            'body':json.dumps('Error in executing the lambda function.')
        }
        
    # Finished!
    return ("Lambda finished")
