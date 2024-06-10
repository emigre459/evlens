import requests
from bs4 import BeautifulSoup
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)
genai.configure(api_key = os.getenv('GEMINI_API_KEY'))


def query_llm(query, model):
    response = model.generate_content(query) # Generate response
    return response.text


def read_html_and_generate_code(model):
  # dictionary of all the links to be webscraped.
  # You can add more if you want to
#    links = {
#        "1":["DST","https://dst.gov.in/call-for-proposals"],
#        "2":["BIRAC","https://birac.nic.in/cfp.php"]
#    }
#    for i in range(1,3):
#        url = links[str(i)][1] # Get URL of each organization
#        r = requests.get(url) # Request for data
#        soup = BeautifulSoup(r.text, 'html.parser') # Parse the HTML elements
#        data = soup.text # Get raw data in string format
#        link = soup.find_all('a', href=True) # Get list of all links on the site in html formet
#        l = ""
#        for a in link:
#            l = l +"\n"+ a['href'][1:] # Get the actual links
      # Create a query
    #    query = data + "name of organization is"+links[str(i)][0]+ "Jumbled links of calls for proposals:"+l+"\n Create a table with the following columns: Call for proposals or joint call for proposals along with respective link, opening date, closing date and the name of the organization."
    #    query_llm(query, model)
    
    url = "https://www.plugshare.com/location/10000"
    # r = requests.get(url)
    
    with open('data/raw/webpage_content.txt') as f:
        doc = f.read()
    # soup = BeautifulSoup(r.text, 'html.parser') # Parse the HTML elements
    # data = soup.text # Get raw data in string format
    # print(data[:10_000])
    query = f"""
    You will find in DATA below some html for a webpage. When accessing the webpage with as a human user in Chrome browser, a Manage Settings link for rejecting cookies appears. When running code in python with the selenium package, however, the Manage Settings link never populates. Why is that?
    
    DATA: {doc}
    """
    return query_llm(query, model)
    
       
if __name__ == '__main__':
    model = genai.GenerativeModel('gemini-pro')
    results = read_html_and_generate_code(model)
    print(results)