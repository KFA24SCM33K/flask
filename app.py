'''
Goal of Flask Microservice:
1. Flask will take the repository_name such as angular, angular-cli, material-design, D3 from the body of the api sent from React app and 
   will utilize the GitHub API to fetch the created and closed issues. Additionally, it will also fetch the author_name and other 
   information for the created and closed issues.
2. It will use group_by to group the data (created and closed issues) by month and will return the grouped data to client (i.e. React app).
3. It will then use the data obtained from the GitHub API (i.e Repository information from GitHub) and pass it as a input request in the 
   POST body to LSTM microservice to predict and forecast the data.
4. The response obtained from LSTM microservice is also return back to client (i.e. React app).

Use Python/GitHub API to retrieve Issues/Repos information of the past 1 year for the following repositories:
- https: // github.com/angular/angular
- https: // github.com/angular/material
- https: // github.com/angular/angular-cli
- https: // github.com/d3/d3
'''
# Import all the required packages 
import os
from flask import Flask, jsonify, request, make_response, Response
from flask_cors import CORS
import json
import dateutil.relativedelta
from dateutil import *
from datetime import date
import pandas as pd
import requests
from datetime import datetime as dt

# Initilize flask app
app = Flask(__name__)
# Handles CORS (cross-origin resource sharing)
CORS(app)

def callApi(url, jsonBody):
    
    try:
        response = requests.post(url, json=jsonBody, headers={'content-type': 'application/json'})
        
        if response.status_code == 500:
            try:
                print("Error Details (JSON):", response.json())
            except ValueError:
                print("Error Details (Text):", response.text)
            except Exception as err:
                print(f"An error occurred: {err}")
        elif response.status_code == 200:
            return response.json()
        
        response.raise_for_status()

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    #returns empty data in case of error
    return {}


# Add response headers to accept all types of  requests
def build_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods",
                         "PUT, GET, POST, DELETE, OPTIONS")
    return response

# Modify response headers when returning to the origin
def build_actual_response(response):
    response.headers.set("Access-Control-Allow-Origin", "*")
    response.headers.set("Access-Control-Allow-Methods",
                         "PUT, GET, POST, DELETE, OPTIONS")
    return response

'''
API route path is  "/api/forecast"
This API will accept only POST request
'''
@app.route('/api/github', methods=['POST'])
def github():
    body = request.get_json()
    # Extract the choosen repositories from the request
    repo_name = body['repository']
    # Add your own GitHub Token to run it local
    token = os.environ.get(
        'GITHUB_TOKEN', 'YOUR_GITHUB_TOKEN')
    GITHUB_URL = f"https://api.github.com/"
    
    if repo_name[0] == 'X':
        stars_count=[]
        repo_list = repo_name.split()
        repo_list.pop(0)
        for i in repo_list:
            GITHUB_URL = f"https://api.github.com/"
            headers = {
            "Authorization": f'token {token}'
            }
            params = {
            "state": "open"
            }
            repository_url = GITHUB_URL + "repos/" + i
            # Fetch GitHub data from GitHub API
            repository = requests.get(repository_url, headers=headers)
            # Convert the data obtained from GitHub API to JSON format
            repository = repository.json()
            stars_count.append([i.split("/")[1], repository["stargazers_count"]])
        json_response_stars = {
        "stars": stars_count
        }
        print(json_response_stars)
        return jsonify(json_response_stars)
    
    elif repo_name[0] == 'Y':
        fork_count=[]

        repo_list = repo_name.split()
        repo_list.pop(0)
        for i in repo_list:
            GITHUB_URL = f"https://api.github.com/"
            headers = {
            "Authorization": f'token {token}'
            }
            params = {
            "state": "open"
            }
            print(headers)
            repository_url = GITHUB_URL + "repos/" + i
            # Fetch GitHub data from GitHub API
            repository = requests.get(repository_url, headers=headers)
            # Convert the data obtained from GitHub API to JSON format
            repository = repository.json()
            print(repository)
            fork_count.append([i.split("/")[1], repository["forks_count"]])
        json_response_fork = {
        "forks": fork_count
        }
        print(json_response_fork)
        return jsonify(json_response_fork)
    

    
    
    headers = {
        "Authorization": f'token {token}'
    }
    params = {
        "state": "open"
    }
    repository_url = GITHUB_URL + "repos/" + repo_name
    # Fetch GitHub data from GitHub API
    repository = requests.get(repository_url, headers=headers)
    # Convert the data obtained from GitHub API to JSON format
    repository = repository.json()
    
    


    today = date.today()

    issues_reponse = []
    pull_req_response = []
    commit_response = []
    # Iterating to get issues for every month for the past 24 months
    for i in range(24):
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        types = 'type:issue'
        repo = 'repo:' + repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 300
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=300'
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types + ' ' + repo + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL + "search/issues?q=" + search_query + "&" + per_page
        # requsets.get will fetch requested query_url from the GitHub API
        search_issues = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        issues_items = []
        try:
            # Extract "items" from search issues
            issues_items = search_issues.get("items")
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        if issues_items is None:
            continue
        for issue in issues_items:
            label_name = []
            data = {}
            current_issue = issue
            # Get issue number
            data['issue_number'] = current_issue["number"]
            # Get created date of issue
            data['created_at'] = current_issue["created_at"][0:10]
            if current_issue["closed_at"] == None:
                data['closed_at'] = current_issue["closed_at"]
            else:
                # Get closed date of issue
                data['closed_at'] = current_issue["closed_at"][0:10]
            for label in current_issue["labels"]:
                # Get label name of issue
                label_name.append(label["name"])
            data['labels'] = label_name
            # It gives state of issue like closed or open
            data['State'] = current_issue["state"]
            # Get Author of issue
            data['Author'] = current_issue["user"]["login"]
            issues_reponse.append(data)

        today = last_month

    df = pd.DataFrame(issues_reponse)
    
    #fetch pull requests data
    for i in range(24):
        per_page = 'per_page=100'
        page = 'page='
        search_query = repo_name + '/pulls?state=all' + "&" + per_page+ "&" + page + f'{i}'
        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL + "repos/" + search_query
        # requsets.get will fetch requested query_url from the GitHub API
        search_pull_requests = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_pull_requests = search_pull_requests.json()
        pull_items = []
        pull_items = search_pull_requests
        if pull_items is None:
            continue
        for pull_req in pull_items:
            label_name = []
            data = {}
            current_pull_req = pull_req
            # Get issue number
            created_at_date = dt.strptime(current_pull_req["created_at"][0:10], "%Y-%m-%d")
            max_date = dt.strptime("2022-11-19", "%Y-%m-%d")
            if created_at_date > max_date:
                data['pull_req_number'] = current_pull_req["number"]
                # Get created date of issue
                data['created_at'] = current_pull_req["created_at"][0:10]
                if current_pull_req["closed_at"] == None:
                    data['closed_at'] = current_pull_req["closed_at"]
                else:
                    # Get closed date of issue
                    data['closed_at'] = current_pull_req["closed_at"][0:10]
                for label in current_pull_req["labels"]:
                    # Get label name of issue
                    label_name.append(label["name"])
                data['labels'] = label_name
                # It gives state of issue like closed or open
                data['State'] = current_pull_req["state"]
                # Get Author of issue
                data['Author'] = current_pull_req["user"]["login"]
                pull_req_response.append(data)
        
    
    #commit data fetching
    n=0
    for i in range(60):
        per_page = 'per_page=100'
        page = 'page='
        search_query = per_page+ "&" + page + f'{i}'
        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL + "repos/" + repo_name + "/commits?" + search_query
        # requsets.get will fetch requested query_url from the GitHub API
        search_commits = requests.get(query_url, headers=headers, params=params)
        # Convert the data obtained from GitHub API to JSON format
        search_commits = search_commits.json()
        #print(search_commits)

        commits_items = []
        commits_items = search_commits
        if commits_items is None:
            continue
        for commit_req in commits_items:
            label_name = []
            data = {}
            current_commit = commit_req
            # Get issue number
            #print("pulls: \n",current_commit)
            created_at_date = dt.strptime(current_commit["commit"]["committer"]["date"][0:10], "%Y-%m-%d")
            max_date = dt.strptime("2022-11-19", "%Y-%m-%d")
            if created_at_date > max_date:
                n=n+1
                data['commit_number'] = n
                # Get created date of issue
                data['created_at'] = current_commit["commit"]["committer"]["date"][0:10]
                commit_response.append(data)
    


    # Daily Created Issues
    print(df.tail())
    df_created_at = df.groupby(['created_at'], as_index=False).count()
    dataFrameCreated = df_created_at[['created_at', 'issue_number']]
    dataFrameCreated.columns = ['date', 'count']
    
    '''
    Weekly Created Issues
    Format the data by grouping the data by month
    ''' 
    created_at = df['created_at']
    week_issue_created = pd.to_datetime(
        pd.Series(created_at), format='%Y-%m-%d')
    week_issue_created.index = week_issue_created.dt.to_period('W')
    week_issue_created = week_issue_created.groupby(level=0).size()
    week_issue_created = week_issue_created.reindex(pd.period_range(
        week_issue_created.index.min(), week_issue_created.index.max(), freq='W'), fill_value=0)
    week_issue_created_dict = week_issue_created.to_dict()
    week_created_at_issues = []
    for key in week_issue_created_dict.keys():
        array = [str(key), week_issue_created_dict[key]]
        week_created_at_issues.append(array)

    '''
    Weekly Closed Issues
    Format the data by grouping the data by month
    ''' 
    
    closed_at = df['closed_at'].sort_values(ascending=True)
    week_issue_closed = pd.to_datetime(
        pd.Series(closed_at), format='%Y-%m-%d')
    week_issue_closed.index = week_issue_closed.dt.to_period('W')
    week_issue_closed = week_issue_closed.groupby(level=0).size()
    week_issue_closed = week_issue_closed.reindex(pd.period_range(
        week_issue_closed.index.min(), week_issue_closed.index.max(), freq='W'), fill_value=0)
    week_issue_closed_dict = week_issue_closed.to_dict()
    week_closed_at_issues = []
    for key in week_issue_closed_dict.keys():
        array = [str(key), week_issue_closed_dict[key]]
        week_closed_at_issues.append(array)

    '''
    Monthly Created Issues
    Format the data by grouping the data by month
    ''' 
    created_at = df['created_at']
    month_issue_created = pd.to_datetime(
        pd.Series(created_at), format='%Y-%m-%d')
    month_issue_created.index = month_issue_created.dt.to_period('M')
    month_issue_created = month_issue_created.groupby(level=0).size()
    month_issue_created = month_issue_created.reindex(pd.period_range(
        month_issue_created.index.min(), month_issue_created.index.max(), freq='M'), fill_value=0)
    month_issue_created_dict = month_issue_created.to_dict()
    created_at_issues = []
    for key in month_issue_created_dict.keys():
        array = [str(key), month_issue_created_dict[key]]
        created_at_issues.append(array)

    '''
    Monthly Closed Issues
    Format the data by grouping the data by month
    ''' 
    
    closed_at = df['closed_at'].sort_values(ascending=True)
    month_issue_closed = pd.to_datetime(
        pd.Series(closed_at), format='%Y-%m-%d')
    month_issue_closed.index = month_issue_closed.dt.to_period('M')
    month_issue_closed = month_issue_closed.groupby(level=0).size()
    month_issue_closed = month_issue_closed.reindex(pd.period_range(
        month_issue_closed.index.min(), month_issue_closed.index.max(), freq='M'), fill_value=0)
    month_issue_closed_dict = month_issue_closed.to_dict()
    closed_at_issues = []
    for key in month_issue_closed_dict.keys():
        array = [str(key), month_issue_closed_dict[key]]
        closed_at_issues.append(array)

    '''
        1. Hit LSTM Microservice by passing issues_response as body
        2. LSTM Microservice will give a list of string containing image paths hosted on google cloud storage
        3. On recieving a valid response from LSTM Microservice, append the above json_response with the response from
            LSTM microservice
    '''
    created_at_body = {
        "issues": issues_reponse,
        "type": "created_at",
        "repo": repo_name.split("/")[1]
    }
    closed_at_body = {
        "issues": issues_reponse,
        "type": "closed_at",
        "repo": repo_name.split("/")[1]
    }
    pull_request_body = {
        "pull": pull_req_response,
        "type": "pull_request",
        "repo": repo_name.split("/")[1]
    }
    commits_body = {
        "pull": commit_response,
        "type": "commits",
        "repo": repo_name.split("/")[1]
    }

    # Update your Google cloud deployed LSTM app URL (NOTE: DO NOT REMOVE "/")
    LSTM_API_URL = "https://lstm-1-864929836925.us-central1.run.app/" + "api/forecast"
    LSTM_API_BASE_URL = "https://lstm-1-864929836925.us-central1.run.app/"

    '''
    Trigger the LSTM microservice to forecasted the created issues
    The request body consists of created issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''
    print("pulling LSTM")
    #LSTM Keras
    created_at_response = callApi(LSTM_API_URL, created_at_body)
    pull_request_rpnse = callApi(LSTM_API_BASE_URL+"api/pulls", pull_request_body)
    commits_respnse = callApi(LSTM_API_BASE_URL+"api/commits", commits_body)
    closed_at_response = callApi(LSTM_API_URL, closed_at_body)
    
    
    print("pulling FB Prophet")
    #Facebook Prophet
    created_at_response_fb = callApi(LSTM_API_BASE_URL+"api/fbprophetis", created_at_body)
    closed_at_fb_response = callApi(LSTM_API_BASE_URL+"api/fbprophetisc", closed_at_body)
    pull_request_fb_rpnse = callApi(LSTM_API_BASE_URL+"api/fbprophetpull", pull_request_body)
    commits_fb_respnse = callApi(LSTM_API_BASE_URL+"api/fbprophetcommits", commits_body)
    
    
    print("pulling Stats")
    #stats model
    created_at_response_stat = callApi(LSTM_API_BASE_URL+"api/statmis", created_at_body)  
    closed_at_response_stat = callApi(LSTM_API_BASE_URL+"api/statmisc", closed_at_body)  
    pull_request_rpnse_stat = callApi(LSTM_API_BASE_URL+"api/statmpull", pull_request_body)
    commits_respnse_stat = callApi(LSTM_API_BASE_URL+"api/statmcommits", commits_body)    
   
        
    '''
    Trigger the LSTM microservice to forecasted the closed issues
    The request body consists of closed issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''    
    
    
    '''
    Create the final response that consists of:
        1. GitHub repository data obtained from GitHub API
        2. Google cloud image urls of created and closed issues obtained from LSTM microservice
    '''
    json_response = {
        "created": created_at_issues,
        "closed": closed_at_issues,
        "starCount": repository["stargazers_count"],
        "forkCount": repository["forks_count"],
        "createdAtImageUrls": created_at_response,
        "closedAtImageUrls": closed_at_response,
        "created_weekly": week_created_at_issues,
        "closed_weekly": week_closed_at_issues,
        "fb_createdAtImageUrls": created_at_response_fb,
        "fb_closedAtImageUrls": closed_at_fb_response,
        "fb_pullReqImageUrls": pull_request_fb_rpnse,
        "fb_commitsImageUrls": commits_fb_respnse,
         "pullReqImageUrls": pull_request_rpnse,
        "commitsImageUrls": commits_respnse,
        "stat_createdAtImageUrls": created_at_response_stat,
        "stat_closedAtImageUrls": closed_at_response_stat,
        "stat_pullReqImageUrls": pull_request_rpnse_stat,
        "stat_commitsImageUrls": commits_respnse_stat,
    }
    # Return the response back to client (React app)
    return jsonify(json_response)


# Run flask app server on port 5000
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
