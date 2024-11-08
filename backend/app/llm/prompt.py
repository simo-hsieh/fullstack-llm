from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from app.models import InfringementCheckResponse

# Build prompt
template = """
query: {query}
Patent Infringement definition:
    Patent infringement occurs when a party makes, uses, sells, or offers to sell a patented invention without
    permission from the patent holder. In essence, it means violating the exclusive rights granted to the patent
    owner, typically leading to legal disputes.
Input: 
    company names: {company_name}
    patent claim: {patent_claim}
Instruction:
class InfringingProduct(BaseModel):
    product_name: str
    infringement_likelihood: str
    relevant_claims: List[str]
    explanation: str
    specific_features: List[str]

class InfringementCheckResponse(BaseModel):
    analysis_id: str 
    patent_id: str
    company_name: str
    analysis_date: str
    top_infringing_products: List[InfringingProduct]
    overall_risk_assessment: str 

The out put format should be json of InfringementCheckResponse.
definitions:
  infringement_likelihood: "High" or "Moderate" or "Low"
  relevant_claims: index of the claim, such as ["1", "2", "3", "20", "21"] 
  explanation: the relevant reasons, such as "The Walmart Shopping App implements several key
    elements of the patent claims including the direct advertisement-to-list
    functionality, mobile application integration, and shopping list
    synchronization. The app's implementation of digital advertisement display
    and product data handling closely matches the patent's specifications.",
  specific_features: related features in the product description, such as [
    "Direct advertisement-to-list functionality",
    "Mobile app integration",
    "Shopping list synchronization",
    "Digital weekly ads integration",
    "Product data payload handling"
    ]
  "overall_risk_assessment": a summary, such as "High risk of infringement due to
    implementation of core patent claims in multiple products, particularly
    the Shopping App which implements most key elements of the patent claims.
    Walmart+ presents additional moderate risk through its partial
    implementation of the patented technology."

context: {context}

response:
"""
# Set up a parser + inject instructions into the prompt template.
parser = PydanticOutputParser(pydantic_object=InfringementCheckResponse)
# QA_CHAIN_PROMPT = ChatPromptTemplate.from_template(template)
QA_CHAIN_PROMPT = PromptTemplate(input_variables=["query", "context", "company_name", "patent_claim"], template=template,partial_variables={"format_instructions": parser.get_format_instructions()},)