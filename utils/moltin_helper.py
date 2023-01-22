import requests


def get_access_token(client_id, client_secret):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()

    return response.json()['access_token']


def get_products(access_token, product_id=None):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    url = f'https://api.moltin.com/v2/products/{product_id}' if product_id else 'https://api.moltin.com/v2/products'

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_file(access_token, file_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}', headers=headers)
    response.raise_for_status()

    return response.json()


def add_product_to_cart(access_token, cart_id, product, quantity=1):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    json_data = {
        'data': {
            'id': product['id'],
            'type': 'cart_item',
            'quantity': quantity,
        },
    }

    response = requests.post(f'https://api.moltin.com/v2/carts/{cart_id}/items', headers=headers, json=json_data)
    response.raise_for_status()

    return response.json()


def get_cart(access_token, cart_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}', headers=headers)
    response.raise_for_status()

    return response.json()


def get_cart_items(access_token, cart_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_id}/items', headers=headers)
    response.raise_for_status()

    return response.json()


def remove_cart_item(access_token, cart_id, cart_item_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.delete(f'https://api.moltin.com/v2/carts/{cart_id}/items/{cart_item_id}', headers=headers)
    response.raise_for_status()

    return response.json()


def create_customer(access_token, email):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    json_data = {
        'data': {
            'type': 'customer',
            'name': email.split('@')[0],
            'email': email,
            'password': 'mysecretpassword',
        },
    }

    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=json_data)
    response.raise_for_status()

    return response.json()


def get_customer(access_token, customer_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(f'https://api.moltin.com/v2/customers/{customer_id}', headers=headers)
    response.raise_for_status()

    return response.json()
