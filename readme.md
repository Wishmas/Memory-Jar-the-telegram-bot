# Бот для заучивания слов и терминов

---

![preview](bot_gif.gif)

---

## Описание проекта
В рамках данной работы я создал телеграм-бота, способного через взаимодействие с базой данных Postgresql создавать для пользователя персональную таблицу из пар термин-перевод, а затем выполнять с ними различные манипуляции. Полный список команд бота таков:

- /instruct - вызывает инструкцию с описанием возможностей бота
- /create - создает персональную таблицу пользователя
- /end - очищает персональную таблицу пользователя
- /result - выводит персональную таблицу на экран
- add "термин" : "перевод" - добавляет новую пару в таблицу
- переведи "термин" - выводит пару к указанному слову
- удали "термин" - удаляет пару с указанным термином
- поменяй "термин" : "перевод" - заменяет пару указанного слова на другую
- /learn - запускает режим заучивания

Режим заучивания является основной функцией бота, поскольку он позволяет не просто хранить слова в словаре, но и целенаправленно заучивать их. После активации режима бот начинает в случайном порядке отправлять пользователю термины из его таблицы и просить написать перевод. Процесс продолжается, пока пользователь не напишет "стоп". После выхода из режима заучивания пользователь получает статистику о количестве своих правильных и неправильных ответов. 

---

Сам бот и база данных были созданы и тестировались на локальном устройстве и на данный момент недоступны за его пределами, однако подобную базу очень просто воссоздать, поскольку в ней должна быть лишь одна пустая схема "tbb", в которой программа будет автоматически создавать и заполнять таблицы. Этот процесс происходит через телеграм-IP пользователя, поэтому любые противоречния при использовании бота несколькими людьми одновременно исключены. 

Для взаимодействия с telegram использовалась библиотека telebot, а для взаимодействия с БД - psycopg2.
