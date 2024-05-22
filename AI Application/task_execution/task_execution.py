from client.llm_connection import LLMConnection
from data_preparation.data_generation import Data_Generation
from data_preparation.data_processing import Data_Processing
from data_preparation.prompt_template import Prompt_Template
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain.agents import AgentExecutor, create_react_agent, Tool
import gradio as gr
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from crewai import Crew, Process
from langchain.chains import TransformChain
from langchain_core.runnables import chain

llm_connection = LLMConnection()
data_generation = Data_Generation()
data_processing = Data_Processing()
prompt_template = Prompt_Template()

class Task_Execution:
    def __init__(self):
        self.ollama = llm_connection.connect_ollama()
        self.chat_ollama = llm_connection.connect_chat_ollama()

    def execute_automate_browsing(self, search_query):
        # Pull the ReAct prompting approach prompt to be used as base
        prompt = data_generation.get_react_prompting()
        serper_wrapper = GoogleSerperAPIWrapper()
        tools = [
            Tool(
                name="Intermediate Answer",
                description="Search Google and return the first result.",
                func=serper_wrapper.run,
            )
        ]
        agent = create_react_agent(self.chat_ollama, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
        output = agent_executor.invoke({"input": search_query})

        return output


    def gradio_interface(self):
        iface = gr.ChatInterface(
            fn = self.querying,
            chatbot=gr.Chatbot(height=600),
            textbox=gr.Textbox(placeholder="Tell me about Stripe System Design Articles?", container=False, scale=7),
            title="MLSystemDesignBot",
            theme="soft",
            examples=["How to design a System for Holiday Prediction like Doordash?",
                                "Please summarize Expedia Group's Customer Lifetime Value Prediction Model"],
            cache_examples=True,
            retry_btn="Retry",
            undo_btn="Undo",
            clear_btn="Clear",
            submit_btn="Submit"
                )

        return iface

    def querying(self, query, history):
        db = data_processing.store_docs_in_db("Give me an indepth Recommendation System ML System Design")
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.ollama,
            retriever=db.as_retriever(search_kwargs={"k": 2}),
            memory=memory,
            condense_question_prompt=prompt_template.interview_bot_template(),
        )
        result = qa_chain({"question": query})
        return result["answer"].strip()

    def execute_crewai(self):
        agent1, agent2, agent3, agent4 = prompt_template.crewai_template()
        # Initialize a Crew with Agents, Tasks, and set the process to hierarchical
        crew = Crew(
            agents=[agent1.agent, agent2.agent, agent3.agent, agent4.agent],
            tasks=[agent1.task, agent2.task, agent3.task, agent4.task],
            llm=self.ollama,
            process=Process.sequential,
            verbose=True,
        )
        return crew.kickoff()
        
    @staticmethod
    @chain
    def image_model(inputs: dict) -> str | list[str] | dict:
        """Invoke model with image and prompt."""
        image = data_processing.image_processing(inputs)["image"]
        multi_model = llm_connection.connect_mulimodel_ollama()
        multi_model.bind(images=image)
        msg = multi_model.invoke(
            [
                {"role": "system", "content": "you are a usefull assistant that provides information about images"},
                {"role": "user", "content": inputs["prompt"]},
            ]
        )
        return msg

    def get_image_informations(self, image_path: str) -> dict:
        load_image_chain = TransformChain(
        input_variables=['image_path'],
        output_variables=['image'],
        transform=data_processing.image_processing
        )
        image_model = self.image_model
        vision_chain = load_image_chain | image_model
        output = vision_chain.invoke({'image_path': f'{image_path}', 'prompt': prompt_template.get_image_info_prompt()})
        print('Input Prompt:', prompt_template.get_image_info_prompt())
        return output