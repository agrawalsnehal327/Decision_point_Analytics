import os
import autogen
from autogen import AssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import UserProxyAgent
import chromadb

llm_config = {
    "timeout": 600,
    "cache_seed": 44,  # change the seed for different trials
    "config_list": [{"model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"]}],
    "temperature": 0
}

def termination_msg(x):
    return isinstance(x, dict) and "TERMINATE" == str(x.get("content", ""))[-9:].upper()

from autogen import ConversableAgent

user = ConversableAgent(
    name="user",
    llm_config=False,
    is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
)

fin_aid = RetrieveUserProxyAgent(
    name="FinanceRetrieveAgent",
    human_input_mode="NEVER",
    retrieve_config={
        "task": "qa",
        "docs_path": ["limited_output2.txt", "limited_output.txt"],
        "chunk_token_size": 2000,
        "model": "gpt-3.5-turbo",
        "collection_name":"finance",
        "overwrite":True,
        "update_context":False,
        "get_or_create": True,



        
    },
    code_execution_config=False,
)

sales_aid = RetrieveUserProxyAgent(
    name="SalesRetrieveAgent",
    human_input_mode="NEVER",
    retrieve_config={
        "task": "qa",
        "docs_path": ["sales_data.csv"],
        "chunk_token_size": 2000,
        "model": "gpt-3.5-turbo",
        "collection_name":"sales",
        "overwrite":True,
        "update_context":False,
        "get_or_create" : True,


    },
    code_execution_config=False,
)





Inventory_aid = RetrieveUserProxyAgent(
    name="InventoryRetrieveAgent",
    human_input_mode="NEVER",
    retrieve_config={
        "task": "qa",
        "docs_path": ["daily_inventory_data.csv"],
        "chunk_token_size": 2000,
        "model": "gpt-3.5-turbo",
        "collection_name":"inv",
        "overwrite":True,
        "update_context":False,
        "get_or_create" : True,
    
       
    },
    code_execution_config=False,
)

finance_data = AssistantAgent(
    name="Finance_data_support",
    is_termination_msg=termination_msg,
    system_message= """
    , your work only to **call registered function** ,
""",
    llm_config=llm_config,
)

finance = AssistantAgent(
    name="Finance_Analyst",
    is_termination_msg=termination_msg,
    system_message= """
"Finance Analyst Role Definition":

**Behave Like a Finance Expert:

Provide insights and answers strictly within the realm of finance.
Maintain professional conduct and ensure all advice is financially sound and backed by thorough analysis.
Offer solutions and recommendations for financial problems, investment opportunities, and risk management.

** You are also judge you can check sentiment of current context suggested.

**Use Chain-of-Thought (CoT) Reasoning Approach:

Break down complex financial queries into manageable steps.
Explain the rationale behind each step of the analysis, ensuring clarity and transparency in the decision-making process.
Use a logical and structured approach to address financial questions and solve problems.
Provide Answers, Views, and Sentiment-Based Nudges:

Deliver precise answers to financial questions, integrating your own expert views and the sentiment of the financial market.
Use current financial sentiment to guide users on potential actions they can take, whether it's buying, holding, or selling assets, or making other financial decisions.
Offer actionable insights based on market trends, financial news, and economic indicators to help users make informed decision.

**** provide a short nudge(MUST) with flow up question**
""",
    max_consecutive_auto_reply=1,
    llm_config=llm_config,
)


sales_data = AssistantAgent(
    name="sales_data_support",
    is_termination_msg=termination_msg,
    system_message= """
    your work only to **call registered function** ,
""",
    llm_config=llm_config,
)

sales = AssistantAgent(
    name="Sales_Analyst",
    is_termination_msg=termination_msg,
    system_message=  """
Generate detailed reports on sales performance, trends, and issues.
Behave Like a Sales Expert:

Provide insights and solutions strictly within the realm of sales.
Address sales problems, identify opportunities for improvement, and suggest strategies to boost sales.
Use Chain-of-Thought (CoT) Reasoning Approach:

Break down sales issues into manageable steps.
Explain the reasoning behind each step to ensure clarity and effective problem-solving.
Provide Answers, Views, and Sentiment-Based Nudges:

Deliver precise answers to sales-related questions, integrating expert views and current market sentiment.
Offer actionable insights based on sales data trends and customer feedback to help improve sales performance.

    **** provide a short nudge(MUST)**,  redirect to convergence checker.
""",llm_config=llm_config)

inventory = AssistantAgent(
    name="Inventory_Analyst",
    is_termination_msg=termination_msg,
    system_message=  """

     your work only to (MUST)**call registered function** ,
""",
llm_config=llm_config)


verifier = AssistantAgent(
    name="convergence_checker",
    is_termination_msg=termination_msg,
    system_message=" Redirect to next user till reply is  'ALWAYS'",

    llm_config=llm_config,human_input_mode="ALWAYS"
)
def _reset_agents():
   
    finance.reset()
    sales.reset()
    inventory.reset()
   
from typing_extensions import Annotated
def call_rag_chat():
    _reset_agents()

    # In this case, we will have multiple user proxy agents and we don't initiate the chat
    # with RAG user proxy agent.
    # In order to use RAG user proxy agent, we need to wrap RAG agents in a function and call

    # it from other agents.
    def retrieve_content2(
        message: Annotated[
            str,
            "Refined message which keeps the original meaning and can be used to retrieve content for code generation and question answering.",
        ],
        n_results: Annotated[int, "number of results"] = 3,
    ) -> str:
        Inventory_aid.n_results = n_results  # Set the number of results to be retrieved.
        # Check if we need to update the context.
        update_context_case1, update_context_case2 = Inventory_aid._check_update_context(message)
        if (update_context_case1 or update_context_case2) and Inventory_aid.update_context:
            Inventory_aid.problem = message if not hasattr(Inventory_aid, "problem") else Inventory_aid.problem
            _, ret_msg = Inventory_aid._generate_retrieve_user_reply(message)
        else:
            _context = {"problem": message, "n_results": n_results}
            ret_msg = Inventory_aid.message_generator(Inventory_aid, None, _context)
        return ret_msg if ret_msg else message
    
    def retrieve_content(
        message: Annotated[
            str,
            "Refined message which keeps the original meaning and can be used to retrieve content for code generation and question answering.",
        ],
        n_results: Annotated[int, "number of results"] = 1,
    ) -> str:
        sales_aid.n_results = n_results  # Set the number of results to be retrieved.
        # Check if we need to update the context.
        update_context_case1, update_context_case2 = sales_aid._check_update_context(message)
        if (update_context_case1 or update_context_case2) and sales_aid.update_context:
            sales_aid.problem = message if not hasattr(sales_aid, "problem") else sales_aid.problem
            _, ret_msg = sales_aid._generate_retrieve_user_reply(message)
        else:
            _context = {"problem": message, "n_results": n_results}
            ret_msg = sales_aid.message_generator(sales_aid, None, _context)
        return ret_msg if ret_msg else message
    
    def retrieve_content1(
        message: Annotated[
            str,
            "Refined message which keeps the original meaning and can be used to retrieve content for code generation and question answering.",
        ],
        n_results: Annotated[int, "number of results"] = 1,
    ) -> str:
        fin_aid.n_results = n_results  # Set the number of results to be retrieved.
        # Check if we need to update the context.
        update_context_case1, update_context_case2 = fin_aid._check_update_context(message)
        if (update_context_case1 or update_context_case2) and fin_aid.update_context:
            fin_aid.problem = message if not hasattr(fin_aid, "problem") else fin_aid.problem
            _, ret_msg = fin_aid._generate_retrieve_user_reply(message)
        else:
            _context = {"problem": message, "n_results": n_results}
            ret_msg = fin_aid.message_generator(fin_aid, None, _context)
        return ret_msg if ret_msg else message


    fin_aid.human_input_mode = "NEVER"  # Disable human input for fin_aid since it only retrieves content.
    sales_aid.human_input_mode = "NEVER"  # Disable human input for sales_aid since it only retrieves content.

    autogen.agentchat.register_function(
    retrieve_content,
    caller=sales_data,
    executor=user,
    description="retrieve data (RAG) for sales part of user questiom",
)
    autogen.agentchat.register_function(
    retrieve_content1,
    caller=finance_data,
    executor=user,
    description="retrieve data (RAG) for finance part in question",
)

 
    autogen.agentchat.register_function(
    retrieve_content2,
    caller=inventory,
    executor=user,
    description="retrieve data (RAG) for Inventory related like warehouse inventory details part in question",
)
   


    groupchat = autogen.GroupChat(
        agents=[user,inventory,sales_data],
        messages=[],
        max_round=12,
        speaker_selection_method="round_robin",
    )
    llm_config_manager = llm_config.copy()
    llm_config_manager.pop("functions", None)
    llm_config_manager.pop("tools", None)
    manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config_manager,
    is_termination_msg=lambda x: "GROUPCHAT_TERMINATE" in x.get("content", ""), )

    manager = autogen.GroupChatManager(groupchat=groupchat)
    
    
    message = "Why financial risk causes company sames as inventory?"

    user.initiate_chat(manager,
        message=message)
call_rag_chat()

