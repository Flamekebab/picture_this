import server
import model
from helpers import *
from seed_data import data

# * create users * #
for i in data:
    register_user(data[i]['name'], data[i]['email'], data[i]['password'])
    if 'boards' in data[i]:
        for board in data[i]['boards']:
            create_board(board['name'], board['icon'], board['hex_code'], board['user_id'])
    if 'images' in data[i]:
        for image in data[i]['images']:
            upload_image(image['url'], image['notes'], image['user'], image['board_id'], image['private'])

if __name__ == '__main__':
    print("Database seed completed.")
