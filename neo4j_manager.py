from neo4j import GraphDatabase, RoutingControl


class Neo4j_manager:
    def __init__(self, uri:str, user:str, password:str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None


    def connect(self) -> None:
        """Connect to Neo4j"""

        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))       
        

    def neo4j_check_connection(self):
        try:
            self.driver.verify_connectivity()
            print("Connection successful!")
            return True
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            return False
        
    def get_driver(self) -> None:
        return self.driver
      
    def close_driver(self) -> None:
        """Close the driver connection"""
        if self.driver:
            self.driver.close()
            print("Driver closed.")
        else:
            print("No driver connected.")
            
    
    def query_graph(self, query, database, return_chars:list, parameters={}):
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j.")

        records, summary, keys = self.driver.execute_query(
        query,
        parameters_= parameters, database_= database, routing_=RoutingControl.READ,
        )
        results = []
        for char in return_chars:
            results.append([record.data()[char] for record in records]) #the 'a' character changes, based on what we use in the RETURN of the query

        return results

    def user_ingestion(self):
        pass
    