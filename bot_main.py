import mysql.connector
import mysql.connector.pooling
import telebot
import re
import functions as funcs
import bot_config as cfg
import time

bot = telebot.TeleBot(token=cfg.BOT_TOKEN)
conn_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool", pool_size=6, database=cfg.DB_NAME, user=cfg.DB_USER, password=cfg.DB_PASSWORD,host=cfg.DB_HOST)

# Создает новую таблицу:
@bot.message_handler(func=lambda message: message.text.split()[0].lower()=='create')
def create_table(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    table_name = '_'.join(split_message[1:]).lower() if len(split_message) > 1 else None
    if not table_name:
        bot.reply_to(message, 'Вы не указали название таблицы')
    else:
        conn = conn_pool.get_connection()
        cur = conn.cursor()
        if not funcs.table_exists(user_id,table_name,cur):
            command = '''
            insert into table_names (user_id,table_name,table_id,active)
            values (%s, %s, %s, %s);'''
            cur.execute(command,(int(user_id),str(table_name),str(user_name)+'_'+str(table_name),0))
            conn.commit()
            bot.reply_to(message, 'Таблица создана!')
        else:
            bot.reply_to(message, 'Такая таблица уже существует')
        cur.close()
        conn.close()

# Делает таблицу активной:
@bot.message_handler(func=lambda message: message.text.split()[0].lower()=='use')
def use_table(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    table_name = '_'.join(split_message[1:]).lower() if len(split_message) > 1 else None
    if not table_name:
        bot.reply_to(message, 'Вы не указали название таблицы')
    else:
        conn = conn_pool.get_connection()
        cur = conn.cursor()
        if not funcs.table_exists(user_id,table_name,cur):
            bot.reply_to(message, 'Такой таблицы не существует')
        else:
            command = '''
            update table_names
            set active = case
                when table_name = %s then 1
                else 0
            end
            where user_id = %s;'''
            cur.execute(command,(str(table_name),int(user_id)))
            conn.commit()
            bot.reply_to(message, f'Используется таблица {table_name.replace("_"," ")}')
        cur.close()
        conn.close()

# Добавляет в активную таблицу новую пару:
@bot.message_handler(func=lambda message: len(re.findall(r'[\w\s]+:[\w\s]+',message.text))!=0)
def add_pare(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    conn = conn_pool.get_connection()
    cur = conn.cursor()
    table_id = funcs.get_active_table(cur,user_id)
    if not table_id:
        bot.reply_to(message, 'Сначала выберите, какую таблицу использовать')
    else:
        term,trans = re.findall(r'([\w\s]+):([\w\s]+)',message.text)[0]
        term,trans = term.strip().lower(),trans.strip().lower()
        table_id = table_id[0]
        cur.execute('''
        select term from libr
        where table_id = %s and term = %s limit 1;''',(str(table_id),str(term)))
        if cur.fetchone():
            command = '''
            update libr
            set trans = %s
            where term = %s and table_id = %s'''
            cur.execute(command,(str(trans),str(term),str(table_id)))
            conn.commit()
            bot.reply_to(message, 'Заменено')
        else:
            command = '''
            insert into libr (table_id, term, trans)
            values (%s,%s,%s);'''
            cur.execute(command,(str(table_id),str(term),str(trans)))
            conn.commit()
            bot.reply_to(message, 'Добавлено')
    cur.close()
    conn.close()

# Возвращает второе слово из пары:
@bot.message_handler(func=lambda message: message.text[:3].lower().strip()=='get')
def translate(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    conn = conn_pool.get_connection()
    cur = conn.cursor()
    table_id = funcs.get_active_table(cur,user_id)
    if not table_id:
        bot.reply_to(message, 'Сначала выберите, какую таблицу использовать')
    else:
        word = message.text[3:].strip().lower()
        cur.execute('''
        select words from
        (select table_id, case
            when term = %s then trans
            when trans = %s then term
        end AS words
        from libr) as temp
        where words is not null
        and table_id = %s;''',(str(word),str(word),str(table_id[0])))
        answer = cur.fetchall()
        if not answer:
            bot.reply_to(message, 'Такого слова нет в вашем словаре')
        else:
            bot.reply_to(message, '\n'.join([w[0] for w in answer]))
    cur.close()
    conn.close()

# Удаляет пару из активной таблицы:
@bot.message_handler(func=lambda message: message.text[:3].lower().strip()=='del')
def delete(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    conn = conn_pool.get_connection()
    cur = conn.cursor()
    table_id = funcs.get_active_table(cur,user_id)
    if not table_id:
        bot.reply_to(message, 'Сначала выберите, какую таблицу использовать')
    else:
        word = message.text[3:].strip().lower()
        cur.execute("""
        select concat(term,' : ',trans) as pare
        from libr where (table_id = %s and term= %s)
        or (table_id = %s and trans=%s);""", (str(table_id[0]),str(word),str(table_id[0]),str(word)))
        answer = cur.fetchall()
        if not answer:
            bot.reply_to(message, 'Такого слова нет в вашем словаре')
        else:
            cur.execute("""
            delete from libr where (table_id = %s and term=%s)
            or (table_id = %s and trans=%s);""", (str(table_id[0]),str(word),str(table_id[0]),str(word)))
            conn.commit()
            bot.reply_to(message, f'Пара{funcs.bs}{funcs.bs.join([w[0] for w in answer])}{funcs.bs}удалена')
    cur.close()
    conn.close()

# Возвращает список таблиц пользователя:
@bot.message_handler(commands=['tables'])
def my_tables(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    conn = conn_pool.get_connection()
    cur = conn.cursor()
    cur.execute(f'''
    select table_name, active from table_names
    where user_id = {str(user_id)}''')
    tables = cur.fetchall()
    if len(tables)==0:
        bot.reply_to(message, 'У вас пока нет ни одной таблицы')
    else:
        tables = [str(t[0]).replace('_',' ') if t[1]==0 else str(t[0]).replace('_',' ') + ' (сейчас активна)' for t in sorted(tables,key=lambda x: x[1])[::-1]]
        bot.reply_to(message, '\n'.join(tables))
    cur.close()
    conn.close()

# Возвращает все пары из активной таблицы:
@bot.message_handler(commands=['result'])
def print_table(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    conn = conn_pool.get_connection()
    cur = conn.cursor()
    table_id = funcs.get_active_table(cur,user_id)
    if not table_id:
        bot.reply_to(message, 'Сначала выберите, какую таблицу использовать')
    else:
        cur.execute("""
        select concat(term,' : ',trans) as pare
        from libr where table_id = %s;""",(str(table_id[0]),))
        result = cur.fetchall()
        if len(result)==0:
            bot.reply_to(message, 'Эта таблица пуста')
        else:
            result = [t[0] for t in result]
            bot.reply_to(message, '\n'.join(result))
    cur.close()
    conn.close()

# Удаляет активную таблицу:
@bot.message_handler(commands=['drop'])
def drop_table(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    conn = conn_pool.get_connection()
    cur = conn.cursor()
    table_id = funcs.get_active_table(cur,user_id)
    if not table_id:
        bot.reply_to(message, 'Сначала выберите, какую таблицу использовать')
    else:
        table_id = table_id[0]
        cur.execute('''
        select table_name from table_names
        where table_id = %s;''', (str(table_id),))
        table_name = cur.fetchone()[0]
        bot.reply_to(message, f'Если вы уверены, что хотите удалить {table_name}, напишите "да"')
        bot.register_next_step_handler(message,confirmation,table_id,table_name)
    cur.close()
    conn.close()

def confirmation(message,table_id,table_name):
    if message.text.strip().lower() == "да":
        conn = conn_pool.get_connection()
        cur = conn.cursor()
        command = '''
        delete from libr
        where table_id = %s;'''
        cur.execute(command, (str(table_id),))
        conn.commit()
        command = '''delete from table_names
        where table_id = %s;'''
        cur.execute(command,(str(table_id),))
        conn.commit()
        bot.reply_to(message, f'Таблица {table_name} успешно удалена')
        cur.close()
        conn.close()
    else:
        bot.reply_to(message, 'Удаление отменено')

# Запускает режим заучивания:
@bot.message_handler(commands=['learn'])
def learn_mode(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    conn = conn_pool.get_connection()
    cur = conn.cursor()
    table_id = funcs.get_active_table(cur, user_id)
    if not table_id:
        bot.reply_to(message, 'Сначала выберите, какую таблицу использовать')
    else:
        bot.reply_to(message, f'Выберите режим заучивания:{funcs.bs}1 - учить термины по значениям{funcs.bs}2 - учить значения по терминам')
        bot.register_next_step_handler(message, learn_type,table_id[0],conn,cur)

def learn_type(message,table_id,conn,cur):
    cor_cnt = 0
    inc_cnt = 0
    if str(message.text) == "1":
        learn_word(message, table_id, conn, cur, cor_cnt, inc_cnt, word='None', ltype=1)
    elif str(message.text) == "2":
        learn_word(message, table_id, conn, cur, cor_cnt, inc_cnt, word='None', ltype=2)
    else:
        bot.reply_to(message, 'Ошибка, попробуйте еще раз')

def learn_word(message,table_id,conn,cur,cor_cnt,inc_cnt,word,ltype):
    if ltype == 1:
        cur.execute('''
        select term from libr
        where term != %s and table_id = %s
        order by rand() limit 1;''', (str(word), str(table_id)))
    elif ltype == 2:
        cur.execute('''
        select trans from libr
        where trans != %s and table_id = %s
        order by rand() limit 1;''', (str(word), str(table_id)))

    word = ''.join([i for i in cur.fetchone()])
    bot.send_message(message.chat.id, word)
    bot.register_next_step_handler(message, check_word, table_id, conn, cur, cor_cnt, inc_cnt, word, ltype)

def check_word(message,table_id,conn,cur,cor_cnt,inc_cnt,word,ltype):
    if message.text.lower() == 'stop':
        bot.reply_to(message,f'''Твой результат:{funcs.bs}правильных ответов: {cor_cnt}{funcs.bs}неправильных ответов: {inc_cnt} ''')
        cur.close()
        conn.close()
    else:
        if ltype == 1:
            cur.execute('''
            select trans from libr
            where term = %s and table_id = %s''', (str(word), str(table_id)))
        elif ltype == 2:
            cur.execute('''
            select term from libr
            where trans = %s and table_id = %s''', (str(word), str(table_id)))

        ans = ''.join([i for i in cur.fetchone()])
        if message.text.lower() == ans.lower():
            bot.reply_to(message, 'верно!')
            new_cor_cnt = cor_cnt + 1
            new_inc_cnt = inc_cnt
        else:
            bot.reply_to(message, f'ошибка, правильный ответ: {ans}')
            new_cor_cnt = cor_cnt
            new_inc_cnt = inc_cnt + 1
        learn_word(message, table_id, conn, cur, new_cor_cnt, new_inc_cnt, word, ltype)

# Возвращает инструкцию по эксплуатации:
@bot.message_handler(commands=['instruct'])
def instruct(message):
    inst = '''
Я - Memory Jar, бот, который поможет вам с заучиванием иностранных слов и терминов. Вот что я умею:

*create* _имя-таблицы_ - создает новую пустую таблицу;
*use* _имя-таблицы_ - делает выбранную таблицу активной;
_термин_ : _значение_ - добавляет в активную таблицу пару термин-значение;
*get* _слово_ - возвращает пару для _слова_ из активной таблицы;
*del* _слово_ - удаляет пару со _словом_ из активной таблицы;

*/tables* - показывает список ваших таблиц;
*/result* - показывает все пары слов из активной таблицы;
*/drop* - удаляет активную таблицу;
*/learn* - запускает режим заучивания, в котором вы можете попрактиковаться и проверить, насколько хорошо помните слова в активной таблице.\
Чтобы выйти из режима заучивания, введите команду *stop*.

Вы также можете отправить мне текстовый файл, где на каждой сточке будет пара _термин_ : _значение_, и я добавлю эти слова в активную таблицу.
'''
    bot.send_message(message.chat.id, inst, parse_mode= 'Markdown')

# Переносит пары из файла в активную таблицу:
@bot.message_handler(content_types=['document'])
def get_from_file(message):
    user_id, user_name, split_message = funcs.get_user_info(message)
    conn = conn_pool.get_connection()
    cur = conn.cursor()
    table_id = funcs.get_active_table(cur,user_id)
    if not table_id:
        bot.reply_to(message, 'Сначала выберите, какую таблицу использовать')
    else:
        table_id = table_id[0]
        bot.reply_to(message, 'Обработка файла...')
        file_info = bot.get_file(message.document.file_id)
        file = bot.download_file(file_info.file_path)
        for line in file.decode('utf-8').split('\n'):
            if len(re.findall(r'[\w\s]+:[\w\s]+',line))!=0:
                term, trans = re.findall(r'([\w\s]+):([\w\s]+)', line)[0]
                term, trans = term.strip().lower(), trans.strip().lower()
                cur.execute('''
                select term from libr
                where table_id = %s and term = %s limit 1;''', (str(table_id), str(term)))
                if cur.fetchone():
                    command = '''
                    update libr
                    set trans = %s
                    where term = %s and table_id = %s'''
                    cur.execute(command, (str(trans), str(term), str(table_id)))
                    conn.commit()
                else:
                    command = '''
                    insert into libr (table_id, term, trans)
                    values (%s,%s,%s);'''
                    cur.execute(command, (str(table_id), str(term), str(trans)))
                    conn.commit()
        bot.reply_to(message, 'Пары из файла занесены в активную таблицу!')
    cur.close()
    conn.close()

# Поддерживает коннект с Telegram и с БД:
def keep_alive(conn_pool):
    try:
        conn = conn_pool.get_connection()
        cur = conn.cursor()
        cur.execute('select 1;')
        print(cur.fetchone())
        cur.close()
        conn.close()
    except mysql.connector.Error:
        print('База упала(')
        pass

while True:
    keep_alive(conn_pool)
    try:
        bot.infinity_polling(timeout=250)
    except Exception as e:
        print(f"Error occurred: {e}")
        time.sleep(5)