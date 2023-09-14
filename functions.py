bs = '\n'
def get_user_info(message):
    user_id =  message.from_user.id
    user_name = str(message.from_user.username).replace(' ','_')
    split_message = message.text.split() if message.text else None
    return user_id, user_name, split_message

def table_exists(user_id,table_name,cur):
    cur.execute('''
            select table_id from table_names
            where user_id = (%s) and table_name = (%s);''', (int(user_id), str(table_name)))
    return cur.fetchone()

def get_active_table(cur,user_id):
    cur.execute(f'''
    select table_id from table_names
    where user_id = {str(user_id)} and active = 1 limit 1;''')
    table_id = cur.fetchone()
    return table_id




