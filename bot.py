import telebot
import psycopg2
import config as cfg


bot = telebot.TeleBot(token=cfg.BOT_TOKEN)

conn = psycopg2.connect(dbname=cfg.DB_NAME, user=cfg.DB_USER, password=cfg.DB_PASSWORD,
                        host=cfg.DB_HOST,port=cfg.DB_PORT)
cur = conn.cursor()

def check_session(session,conn):
    check = f"""SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='t_{session}'"""
    cur = conn.cursor()
    cur.execute(check)
    return cur.fetchall() or 0

  
@bot.message_handler(commands=['instruct'])
def instruct(message):  
    
    inst = '''Привет! Я здесь, чтобы помочь тебе с запоминанием слов.
Чтобы приступить к заучиванию, сначала создай свой словарик. Для
этого напиши /create, а затем добавляй новые пары при помощи
следующей конструкции: 'add термин : перевод'. Если захочешь
исправить перевод какого-то термина, напиши 'поменяй термин : новый перевод'. 
Чтобы удалить пару из словаря, напиши 'удали термин'. Чтобы
получить термин по переводу или перевод по термину, напиши
'переведи термин' или 'переведи перевод'. Чтобы посмотреть весь
словарик сразу, напиши /result. Чтобы удалить словарь напиши /end.
Когда закончишь с составлением словаря, напиши /learn, чтобы войти
в режим заучивания. Я буду отправлять тебе термины из твоего словаря,
а ты должен будешь вписывать их перевод. Продолжай пока не выучишь все
или пока не захочешь что-то поменять. Тогда напиши 'стоп', и режим заучивания
выключится. Удачи! (Команды исполняются без кавычек)'''
    bot.send_message(message.chat.id,inst.replace('\n',' '))


  
@bot.message_handler(commands=['create'])
def form_dict(message):  
    
    session = message.from_user.id  
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tbb.t_{session} 
                (id BIGSERIAL PRIMARY KEY UNIQUE, 
                    term varchar, 
                    translation varchar)""")
    conn.commit()
    
    bot.reply_to(message,f'Таблица готова')



@bot.message_handler(func=lambda message: message.text.split()[0].lower()=='add')
def add(message):       
    
    session = message.from_user.id
    stop = check_session(session,conn)
    if stop != 0:
        w = ' '.join(message.text.split()[1:])
        if len(w.split(' : ')) == 2:
            w_1 = w.split(' : ')[0].lower()
            w_2 = w.split(' : ')[1].lower()
            cur.execute("""INSERT INTO tbb.t_%(tbl)s (term,translation) VALUES 
                         (%(trm)s, %(trns)s)""",{'trm': str(w_1), 'trns': str(w_2), 'tbl': session})
            conn.commit()           
            bot.reply_to(message,'добавил')
        else:
            bot.reply_to(message,'Чего-то не хватает')
    else:
        bot.reply_to(message,'Сначала начните новую сессию')



@bot.message_handler(commands=['result'])
def result(message):  
    
    session = message.from_user.id
    stop = check_session(session,conn)
    if stop != 0:
        cur.execute(f"""SELECT term,translation FROM tbb.t_{session}""")
        data = ['Твой словарь:']
        bs = '\n'
        for r in cur:
            data.append(' : '.join([str(i) for i in r]))
        bot.reply_to(message,bs.join(data)) 
        
    else:
        bot.reply_to(message,'Сначала начните новую сессию')
        
    
    
@bot.message_handler(commands=['end'])
def end(message):  
    
    session = message.from_user.id
    stop = check_session(session,conn)
    if stop != 0:
        cur.execute(f"""DROP TABLE IF EXISTS tbb.t_{session}""")
        conn.commit()
        bot.reply_to(message,f'Таблица очищена')
    else:
        bot.reply_to(message,'У вас нет активных сессий')
        
        
@bot.message_handler(func=lambda message: message.text.split()[0].lower() == 'переведи')
def find_tr(message):
    
    session = message.from_user.id
    stop = check_session(session,conn)
    if stop != 0:
        w = ' '.join(message.text.split()[1:])
        data = [f"Перевод для '{w}':"]
        bs = '\n'
        cur.execute("""SELECT translation FROM tbb.t_%(tbl)s 
                    WHERE term = %(trm)s""",{'trm': str(w), 'tbl': session})
        for r in cur:
            data.append(' : '.join([str(i) for i in r]))
        cur.execute("""SELECT term FROM tbb.t_%(tbl)s 
                    WHERE translation =  %(trns)s""",{'trns': str(w), 'tbl': session})
        for r in cur:
            data.append(' : '.join([str(i) for i in r]))
            
        bot.reply_to(message,bs.join(data)) 
    
        
@bot.message_handler(func=lambda message: message.text.split()[0].lower() == 'поменяй')
def change(message):
    
    session = message.from_user.id
    stop = check_session(session,conn)
    if stop != 0:
        w = ' '.join(message.text.split()[1:])
        if len(w.split(' : ')) == 2:
            w_1 = w.split(' : ')[0].lower()
            w_2 = w.split(' : ')[1].lower()
            cur.execute('''UPDATE tbb.t_%(tbl)s  
                        SET translation = %(trns)s
                        WHERE term = %(trm)s''',
                        {'trm': str(w_1), 'trns': str(w_2), 'tbl': session})
            conn.commit()           
            bot.reply_to(message,'если было - поменял')
        else:
            bot.reply_to(message,'Чего-то не хватает')
    else:
        bot.reply_to(message,'Сначала начните новую сессию')
        
@bot.message_handler(func=lambda message: message.text.split()[0].lower() == 'удали')
def delt(message):
    
    session = message.from_user.id
    stop = check_session(session,conn)
    if stop != 0:
        w = ' '.join(message.text.split()[1:])
        cur.execute('''DELETE FROM tbb.t_%(tbl)s  
                    WHERE term = %(trm)s''',
                    {'trm': str(w), 'tbl': session})
        conn.commit()           
        bot.reply_to(message,'если было - удалил')

    else:
        bot.reply_to(message,'Сначала начните новую сессию')


def learn_word(message,session,w,cor_cnt,inc_cnt):
    cur.execute('''SELECT term FROM tbb.t_%(tbl)s
                WHERE term != %(trm)s
                ORDER BY random()
                LIMIT 1 ''',{'trm': str(w), 'tbl': session})
    w = ''.join([i for i in cur.fetchone()])
    bot.send_message(message.chat.id,w)
    bot.register_next_step_handler(message,check_word,session,w,cor_cnt,inc_cnt)
        
        
def check_word(message,session,w,cor_cnt,inc_cnt):
    if message.text == 'стоп':
        bs = '\n'
        bot.reply_to(message,f'''Твой результат:{bs}правильных ответов: {cor_cnt}{bs}неправильных ответов: {inc_cnt} ''')
         
    else:
        cur.execute('''SELECT translation FROM tbb.t_%(tbl)s
                    WHERE term = %(trm)s''',{'trm': str(w), 'tbl': session})
        ans = ''.join([i for i in cur.fetchone()])
        if message.text.lower() == ans.lower():
            bot.reply_to(message,'верно!')
            cor_cnt_1 = cor_cnt + 1
            inc_cnt_1 = inc_cnt
        else:
            bot.reply_to(message,f'ошибка, правильный ответ: {ans}')
            inc_cnt_1 = inc_cnt + 1
            cor_cnt_1 = cor_cnt
        learn_word(message,session,w,cor_cnt_1,inc_cnt_1)
    
    
@bot.message_handler(commands=['learn'])
def learn(message):
     
     session = message.from_user.id
     stop = check_session(session,conn)
     if stop != 0:
         cor_cnt = 0
         inc_cnt = 0
         learn_word(message,session,'None',cor_cnt,inc_cnt)
     else:
         bot.reply_to(message,'У вас нет активных сессий')  
         

bot.infinity_polling() 














    
    