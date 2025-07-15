def store_permanent_information(information: str) -> None:
    """
    Store permanent information permanent_knowledge.txt file.
    """
    try:
        with open("permanent_knowledge.txt", "a") as file:
            file.write(information + "\n")
    except Exception as e:
        print(f"Error storing information: {e}")
    
    