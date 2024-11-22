import json

def generate_neo4j_commands():
    # Read users file
    with open('users.json', 'r', encoding='utf-8') as f:
        users_data = json.load(f)

    # Read connections file
    with open('connections.json', 'r', encoding='utf-8') as f:
        connections_data = json.load(f)

    # Start building the Cypher query
    cypher_query = "// Clear database\n"
    cypher_query += "MATCH (n) DETACH DELETE n;\n\n"
    
    cypher_query += "// Create index\n"
    cypher_query += "CREATE INDEX user_id IF NOT EXISTS FOR (u:User) ON (u.id);\n\n"
    
    # Create all users
    cypher_query += "// Create users\n"
    for i, user in enumerate(users_data['reply']):
        if i == 0:
            cypher_query += f"CREATE (u{user['id']}:User {{id: '{user['id']}', username: '{user['username']}'}})\n"
        else:
            cypher_query += f"WITH 1 as dummy\nCREATE (u{user['id']}:User {{id: '{user['id']}', username: '{user['username']}'}})\n"
    
    # Create relationships
    for conn in connections_data['reply']:
        cypher_query += (f"WITH 1 as dummy\n"
                        f"MATCH (u1:User {{id: '{conn['user1_id']}'}}), "
                        f"(u2:User {{id: '{conn['user2_id']}'}}) "
                        f"CREATE (u1)-[:KNOWS]->(u2)\n")
    
    # Remove the last newline and add semicolon
    cypher_query = cypher_query.rstrip() + ";"
    
    # Save to file
    with open('neo4j_commands.cypher', 'w', encoding='utf-8') as f:
        f.write(cypher_query)

    print("Neo4j commands have been generated in 'neo4j_commands.cypher'")

if __name__ == "__main__":
    generate_neo4j_commands()