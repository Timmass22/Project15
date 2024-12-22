from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
import requests
import logging
import os
from dash import Dash, dcc, html
import plotly.express as px
import pandas as pd  # Добавляем импорт pandas

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['DEBUG'] = True  
load_dotenv()

API_KEY='7zyGOysj5V8yZeeVyW990XxsHqKCo54G'

server = app

# Интеграция DASH
dash_app = Dash(__name__, server=server, url_base_pathname='/dash/')

# делаем стандартный лайаут
dash_app.layout = html.Div([
    html.H1("Графики погодных условий"),
    html.P("Данные будут загружены после проверки погоды."),
    html.A("Назад к форме", href="/", style={"fontSize": "20px", "color": "blue"})
])


def fetch_weather_data(city):
    try:
        location_url = f"http://dataservice.accuweather.com/locations/v1/cities/search?apikey={API_KEY}&q={city}&language=ru-ru"
        location_response = requests.get(location_url)
        location_response.raise_for_status()

        location_data = location_response.json()
        if location_data:
            location_key = location_data[0]['Key']
            weather_url = f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}?apikey={API_KEY}&language=ru-ru&details=true"
            weather_response = requests.get(weather_url)
            weather_response.raise_for_status()

            weather_data = weather_response.json()
            return {
                "city": city,
                "temperature": int(weather_data[0]['Temperature']['Metric']['Value']),
                "humidity": weather_data[0]['RelativeHumidity'],
                "wind_speed": weather_data[0]['Wind']['Speed']['Metric']['Value'],
                "precipitation": weather_data[0]['HasPrecipitation'],
                "weather_text": weather_data[0]['WeatherText'],
            }
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе данных о погоде: {e}")
    return None


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/check_weather', methods=['POST'])
def check_weather():
    start_city = request.form['start_city']
    end_city = request.form['end_city']

    # проверяем дупликаты
    if start_city == end_city:
        return render_template('error.html', message="Вы ввели один и тот же город для начала и конца.")

    # собираем данные по погоде с обоих городов
    start_weather_data = fetch_weather_data(start_city)
    end_weather_data = fetch_weather_data(end_city)

    # ловим неправильные города
    if not start_weather_data:
        return render_template('error.html', message=f"Город '{start_city}' не найден.")

    if not end_weather_data:
        return render_template('error.html', message=f"Город '{end_city}' не найден.")

    # сетапим дэш
    setup_dash(start_weather_data, end_weather_data)

    return render_template(
        'result.html',
        start_weather=start_weather_data,
        end_weather=end_weather_data,
    )


def setup_dash(start_weather, end_weather):
    # готовим данные для графиков
    data = [
        {
            "City": start_weather['city'],
            "Parameter": "Температура",
            "Value": start_weather['temperature']
        },
        {
            "City": end_weather['city'],
            "Parameter": "Температура",
            "Value": end_weather['temperature']
        },
        {
            "City": start_weather['city'],
            "Parameter": "Влажность",
            "Value": start_weather['humidity']
        },
        {
            "City": end_weather['city'],
            "Parameter": "Влажность",
            "Value": end_weather['humidity']
        },
        {
            "City": start_weather['city'],
            "Parameter": "Скорость ветра",
            "Value": start_weather['wind_speed']
        },
        {
            "City": end_weather['city'],
            "Parameter": "Скорость ветра",
            "Value": end_weather['wind_speed']
        }
    ]

    # делаем барчарты
    df = pd.DataFrame(data)
    fig = px.bar(
        df,
        x="City",
        y="Value",
        color="Parameter",
        barmode="group",
        title="Сравнение погодных условий"
    )

    # апдейтим лайаут
    dash_app.layout = html.Div([
        html.H1("Графики погодных условий"),
        dcc.Graph(figure=fig),
        html.A("Назад к форме", href="/", style={"fontSize": "20px", "color": "blue"})
    ])

print(f"API_KEY: {API_KEY}")

if __name__ == '__main__':
    app.run(debug=True)


