import openai
import json

# Load the configuration from the file
with open('secretsConfig.json') as config_file:
    config = json.load(config_file)

# Extract the API key
api_key = config["openAIKey"]

# Initialize the OpenAI API client
openai.api_key = api_key

# Inventory provided by the user
inventory = {
    'Cheesy Potatoes': 1,
    'Cheese Taco': 2,
    'Baja Blast': 3,
}

def convert_order_description(order_description):
    formatted_inventory = ', '.join([f'{code} {name}' for name, code in inventory.items()])
    prompt = f"Convert the order description to the desired format (eg. 1 Cheese Taco, 2 Baja Blasts) using the following inventory items: {formatted_inventory}\n\n{order_description}\n\nConverted order: "
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=50,
        stop=None,
        temperature=0,
    )
    return response.choices[0].text.strip()

def generate_sql_queries(order_description):
    orders = order_description.split(', ')
    sql_queries = []

    for order in orders:
        parts = order.strip().split(' ')
        quantity = int(parts[0])
        item_name_parts = parts[1:]
        item_name = ' '.join(item_name_parts)
        modifications = None

        # Check if modifications are provided
        if 'with' in item_name_parts:
            modifications_index = item_name_parts.index('with')
            modifications = ' '.join(item_name_parts[modifications_index + 1:])
            item_name = ' '.join(item_name_parts[:modifications_index])

        if item_name in inventory:
            item_code = inventory[item_name]
            sql_queries.append(f"INSERT INTO outGoingOrders (itemName, modifications, quantity, price)\nVALUES ({item_code}, '{modifications}', {quantity}, {item_code});")

    return '\n'.join(sql_queries)

def main():
    print("Welcome to the SQL Order Generator!")
    print("Provide the inventory in the format 'Item Name: Item Code' (e.g., 'Cheesy Potatoes: 1')")

    print("\nInventory:")
    for item_name, item_code in inventory.items():
        print(f"{item_name}: {item_code}")
    
    order_description = input("\nEnter your order description:")
    
    converted_order = convert_order_description(order_description)
    print("\nConverted Order Description:")
    print(converted_order)
    
    sql_queries = generate_sql_queries(converted_order)
    print("\nGenerated SQL Queries:\n")
    print(sql_queries)

if __name__ == "__main__":
    main()