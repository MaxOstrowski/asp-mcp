def read_permanent_information() -> str:
    """
    Read permanent information from the permanent_knowledge.txt file.
    """
    try:
        with open("permanent_knowledge.txt", "r") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading information: {e}")
        return ""