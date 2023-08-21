import server
import model
from helpers import *
from seed_data import data

os.system('dropdb pt')
os.system('createdb pt')

model.connect_to_db(server.app)
model.db.create_all()

# * create users * #


for i in data:
    register_user(data[i]['name'], data[i]['email'], data[i]['password'])
    if 'boards' in data[i]:
        for board in data[i]['boards']:
            create_board(board['name'], board['icon'], board['hex_code'], board['user_id'])
    if 'images' in data[i]:
        for image in data[i]['images']:
            upload_image(image['url'], image['notes'], image['user'], image['private'], image['board_id'])

if __name__ == '__main__':
    print("Database seed completed.")
