Web Science Capstone Project 
Proposal

Date:
June 16, 2026
Company Name:
Gitabase
Start Up Roles:
PM: Project Manager - Gonzaga, James Cedrick 
FE: Frontend - Cortaza, Shancel 
BE: Backend - Tablizo, Jay , Gonzaga, James Cedrick 
DBA: Database Administrator - Tablizo, Jay 
SQA: Software Quality Assurance - Rivera, Chiarra Marie 


Proposed Title:
LetThemCook: Web-Based AI Chatbot Meal Recommendation and Recipe Catalog with Ranking System
CS Research Categories/Field:
Retrieval-Augmented Generation (RAG), Natural Language Processing (NLP), Artificial Intelligence, Constraint-Based Optimization, Food Sustainability 
TECHNICAL BACKGROUND:


Background of the Study
   Modern households face increasing challenges concerning food waste and food ingredients management, with research emphasizing that AI-driven solutions are highly effective in finding the optimal inventory and reducing environmental footprints [1]. While AI are progressively utilized in commercial hospitality to track and mitigate waste, the application of such technologies at the household level remains an area which requires further research and exploration [1]. Current general purpose Large Language Models (LLMs) often act as generalists that can hallucinate recipes or disregard specific user request or constraints, failing to stipulate the precision required for sustainable household food management [2]. By utilizing a special Retrieval-Augmented Generation (RAG) architecture, this system can accurately predict using verified culinary datasets, ensuring that generated recipes are achievable, and optimized for user's specific inventory, hence producing more accurate predictions [3][4]. This study explores the intersection of sustainable consumption practices and human-computer interaction (HCI), providing a solution that minimizes waste through intelligent and constraint-based logic [2][6].
Statement of the Problem

This study aims to implement a website constraint-based recipe generation system that assists users in minimizing food waste by identifying suitable recipes, based on existing0 inventory of the user. It seeks to address the following specific problems:

1. Development of a retrieval system that maps available ingredient inputs to a structured culinary database [3].
2. Implementation of an AI-driven logic engine that can propose recipes using a subset of provided user ingredients, explicitly categorize ingredients into used and unused categories, and provide actionable suggestions for how to utilize or store unused ingredients [6].
3. To ensure system efficiency by hosting the AI locally [5].


HOW DID OTHERS SOLVE THE PROBLEM?  

Existing solutions for meal planning often rely on centralized, cloud based models that often lack context specific reasoning needed for pantry management [5]. While hospitality industry use AI for inventory control, these are often large, enterprise level scale solutions that are not adapted for the constraints of individual household kitchens [1]. Other research on ingredient based recommendations using AI lacks the generative flexibility to flexibly utilize new instructions based on dynamic and user specific inventory as general purpose AI models fail to respect the practical constraints of utilizing only available resources without hallucinating [2][6]. 
HOW DO YOU PLAN TO SOLVE THE PROBLEM?  

The development of "LetThemCook", an intelligent food assistant that utilizes a Retrieval Augmented Generation (RAG) architecture, would be to provide grounded and reliable results, instead of relying on generic AI models or chatbots [3][4]. For the retrieval phase, the system will use ChromaDB to index a structured recipe database and perform semantic searches to find recipes that closely match the user's ingredient list [3]. For the generation phase, the system will utilize the Llama 3.2 3B model hosted locally via Ollama to synthesize the instructions [5]. By enforcing a strict System Prompt, the AI is explicitly constrained to utilize only ingredients that are currently available from the user's pantry alongside basic kitchen staples [2]. With this study, it will also demonstrate the broader significance of this project using the "Edge AI", where high level decision making occurs entirely on the local machine [5]. This architectural approach directly ensures data sovereignty, drastically reduces latency, and completely eliminates the recurring API costs overhead of cloud based inference, which results in providing a highly sustainable and private solution for regular consumers [5].
REFERENCES: 

​​[1] F. J. et al., "Exploring the potential of AI-driven food waste management strategies used in the hospitality industry for application in household settings," PMC, Jan. 2025.
 
[2] "Harnessing Artificial Intelligence (AI) to Mitigate Food Waste: Innovative Strategies for Sustainable Consumption," ResearchGate, Feb. 2025.
 
[3] "What is RAG (Retrieval Augmented Generation)?," IBM, 2025.
 
[4] "What is retrieval-augmented generation (RAG)?," BCG / McKinsey, Oct. 2024.
 
[5] "Local AI vs Cloud AI: How to Decide What to Own and What to Rent," MindStudio, May 2026.
 
[6] "AI-Powered Food Waste Reduction and Smart Recipe Recommendation System," ResearchGate, Jan 2026.


