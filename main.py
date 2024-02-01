from google.cloud import bigquery
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
from PIL import Image
import tiktoken
import openai
import os
import time
import json


load_dotenv()  # 自動從 .env 檔案讀取變數
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# For Cost Estimation
def num_tokens_from_string(input_string: str, output_string: str):
    """Count the number of total tokens"""
    encoding = tiktoken.get_encoding("cl100k_base")
    input_expense = len(encoding.encode(input_string)) / 1000 * 0.01   # $0.01 / 1k tokens
    output_expense = len(encoding.encode(output_string)) / 1000 * 0.03  # $0.03 / 1k tokens
    total_expense = input_expense + output_expense 
    return (f"此問答約花費:${total_expense}") 

#For Function Calling
def ask_database(query):
  """Function to query Google BigQuery with a provided SQL query."""
  try:
      location = 'your_location'
      project_id = 'your_project_id'
      db_client = bigquery.Client(project=project_id, location=location)

      query_job = db_client.query(query)
      results = query_job.result()  # 等待查詢完成
      df = results.to_dataframe()
      st.write(df.head())
      st.write(f"表格長度: {len(df)}")

      # 將 DataFrame 轉換為 JSON 字符串
      results_json = df.to_json(orient='records')

  except Exception as e:
      results_json = f"query failed with error: {e}"

  return results_json

def assistant():
    if 'client' not in st.session_state:
        # Initialize the client
        st.session_state.client = OpenAI(api_key=OPENAI_API_KEY)
        #先用於計算成本
        st.session_state.system_prompt = """
        As a  Data Analyst Assistant, your primary role is twofold: to respond to user queries by creating tailored SQL queries for the 'Forest 2 - 專注森林' app's database and to deliver valuable business insights. 'Forest-Next' is a productivity tool designed to assist in time management, helping users efficiently organize and optimize their time.
        
        We have provided {metadata file}(about the raw data), and {database_schema file} to let you further know about our database. You should find the most relevant [Event Content] within these files.

        Your action steps:
        1. Understanding User Needs: Initially, focus on comprehending the user's requirements. This involves identifying the specific data they are interested in, such as particular events or dates. Understanding the context of their query is crucial to proceed effectively.

        2. Database Information Retrieval: Once the user's needs are clear, it is imperative to use the retrieval tool to search for specific database elements within the {metadata} and {database_schema} files. This step is crucial for understanding the structure and content of the data. It's essential to find and utilize the most relevant [Event Content] related to the user's query, such as 'event_date', 'event_name', 'params.key', and 'params.value'. Only by identifying these pertinent details in the {metadata} and {database_schema} can the most accurate query be written.

        3. Handling Nested Structures: Pay special attention to nested structures in the database. Consider if it's necessary to use SQL query like [UNNEST(event_params)] to unravel these structures. This is a critical step for accessing deeper levels of data. Always query 'string_value'.

        4. Formulating the SQL Query: First, check if the metric mentioned by the user exists in the {metric_calculation} file. If it does exist, use the provided SQL query directly to retrieve data. If it doesn't exist, then proceed to write your own SQL query. This custom query should be tailored to the user's needs and based on a clear understanding of the database structure, aiming to retrieve the most relevant information from the database. If the user mentions '最近' (recently), you should retrieve data from the last two weeks.

        5. Query Execution and Refinement: Use the ask-database tool to run the SQL query. If the tool returns an empty table or data, it may indicate that the 'event_name' is incorrect. In such cases, please return to step 2 to revisit and find the most relevant data based on a deeper understanding of the database information and the user's needs. If a user wants to retrieve data about [page_view] events, it's important to identify the correct [string.value] associated with these events in the dataset. Don't rely solely on the user's prompt.

        6. Data Visualization: After successfully retrieving the data, focus on presenting it visually. Write and execute code to create charts or graphs that best represent the data. If the user hasn't specified a preference, choose the most appropriate type of visualization.

        7. Insight Analysis: Finally, provide a summary of the insights gleaned from the visual data representation. This should include key findings or patterns observed in the data, adding value to the user's understanding of the query results.

        Remember:
        - Adhere strictly to these steps and think step by step when using the tools to fulfill your task.
        - Continuously verify the accuracy of the results at each step. If doubts persist, revert to the previous step for reassessment and correction.
        - 你必須使用[英文]製作圖表、[繁體中文]回答問題，回答好的話我會給你小費!

        =========
        Output Format:
        <answers for my questions>
        <visualization chart with preview>
        """

        st.session_state.function_description = "Writing a well-structured SQL query suitable for BigQuery."

        st.session_state.tool_description = """
        SQL query extracting info to answer the user's question. Based on the user's input, identify the most relevant 'event_name' and 'event_date' from files. 
        If the query retrieves no data, revisit the {metadata} file to identify and select the most relevant alternative 'event_name'.
        """

        st.session_state.tools_list = [
            {
                "type": "function",
                "function": {
                    "name": "ask_database",
                    "description": st.session_state.function_description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": st.session_state.tool_description
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "retrieval",
            },
            {
                "type": "code_interpreter",
            }
        ]

        #上傳檔案、創建assistant
        st.session_state.metadata_file = st.session_state.client.files.create(
        file=open("/path/to/metadata.csv", "rb"),
        purpose='assistants'
        )
        st.session_state.schema_file = st.session_state.client.files.create(
        file=open("/path/to/schema.json", "rb"),
        purpose='assistants'
        )
        st.session_state.metric_file = st.session_state.client.files.create(
        file=open("/path/to/metric_definition.txt", "rb"),
        purpose='assistants'
        )
 
        st.session_state.assistant = st.session_state.client.beta.assistants.create(
            name="Data Analyst Assistant",
            tools=st.session_state.tools_list,
            instructions=st.session_state.system_prompt,
            model="gpt-4-1106-preview",
            file_ids=[st.session_state.metadata_file.id, 
                      st.session_state.schema_file.id, 
                      st.session_state.metric_file.id]
        )

        #創建聊天室
        st.session_state.thread = st.session_state.client.beta.threads.create()

    message_bot = st.chat_message("assistant")
    message_bot.write(f"Assistant: {st.session_state['name']} 您好! 我是 data team 的小助手，可以回答各種app相關的問題。")

    user_query = st.chat_input("在這裡提出您的問題...")

    if user_query:

        #計入成本
        input_str = (user_query + st.session_state.system_prompt 
        + st.session_state.function_description + st.session_state.tool_description) 
        output_str = ""
        
        st.write(f"你的提問: {user_query}")

        message = st.session_state.client.beta.threads.messages.create(
        thread_id = st.session_state.thread.id,
        role = "user",
        content = user_query,
        )

        run = st.session_state.client.beta.threads.runs.create(
            thread_id = st.session_state.thread.id,
            assistant_id = assistant.id,
        )

        function_calling_time = 0
        assistant_thining_time = 0
        while True:
            #超過5次代表查詢失敗 
            if function_calling_time >= 5 or assistant_thining_time >= 5:
                st.write("今天太多分析工作讓我累壞了，麻煩您提供更充足的資訊協助我進行查詢")
                break

            # Wait for 10 seconds
            time.sleep(10)

            # Retrieve the run status
            run_status = st.session_state.client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread.id,
                run_id=run.id
            )
            #print(run_status.model_dump_json(indent=4))
            
            # If run is completed, get messages
            if run_status.status == 'completed':
                messages = st.session_state.client.beta.threads.messages.list(
                    thread_id=st.session_state.thread.id
                )

                # Loop through messages and print content based on role
                for msg in messages.data[::-1]:                  
                    role = msg.role
                    if role == "assistant":
                        respond = st.chat_message("assistant")
                    elif role == "user":
                        respond = st.chat_message("human")

                    try:
                        # 嘗試提取文本內容
                        content = msg.content[0].text.value
                        if content:
                            output_str += content
                            respond.write(f"{role.capitalize()}: {content}")
                    except AttributeError:
                        # 如果文本內容不存在，處理圖片
                        try:
                            image_id = msg.content[0].image_file.file_id
                            image_file = openai.files.content(image_id)
                            image = Image.open(image_file).resize((1024, 509))
                            text_content = msg.content[1].text.value
                            if text_content:
                                output_str += text_content
                                respond.write(f"{role.capitalize()}: {text_content}")
                            respond.image(image)

                        except Exception as e:
                            respond.write(f"Error processing image: {e}")

                #印出花費
                respond.write(num_tokens_from_string(input_str, output_str))
                break

            elif run_status.status == 'requires_action':
                st.write("Function Calling")
                function_calling_time +=1
                assistant_thining_time = 0  #重製
                required_actions = run_status.required_action.submit_tool_outputs.model_dump()
                
                tool_outputs = []
                for action in required_actions["tool_calls"]:
                    func_name = action['function']['name']

                    try:
                        arguments = json.loads(action['function']['arguments'])
                    except json.JSONDecodeError as e:
                        st.error('解析Json發生錯誤，請重新提問', icon="🚨")
                        st.write(action['function']['arguments'])
                        break

                    if func_name == "ask_database":
                        output_query = arguments['query']
                        # 印出SQL
                        st.code(output_query, language='sql') 
                        #計算輸出字串
                        output_str += output_query          
                        output = ask_database(query=output_query)
                        tool_outputs.append({
                            "tool_call_id": action['id'],
                            "output": output
                        })
                    else:
                        raise ValueError(f"Unknown function: {func_name}")

                st.write("Submitting outputs back to the Assistant...")
                st.session_state.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=st.session_state.thread.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
 
            else:
                assistant_thining_time +=1
                st.write("Waiting for the Assistant to process...")
                time.sleep(20)
                
    # 提供一個按鈕來清除聊天
    if st.button('清除聊天'):
        user_query = False