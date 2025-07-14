from core.llm import LLM

def test_llm_math_answer():
    llm = LLM("")
    # Ask a simple math question
    question = "What is 2 + 2? Answer with a dictionary with one solution entry like this" \
    "{ \"solution\": 42}."
   
    response = eval(llm.ask([question, "user"]))
    # Check the response
    # Accept '4'
    assert { "solution": 4 } == response, f"Unexpected LLM answer: {response}"
