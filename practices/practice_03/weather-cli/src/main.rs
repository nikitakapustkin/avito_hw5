use clap::Parser;
use colored::Colorize;
use serde::Deserialize;

#[derive(Parser)]
#[command(name = "weather", about = "Получить текущую погоду для города")]
struct Args {
    /// Название города
    city: String,

    /// Вывести сырой JSON ответ
    #[arg(long)]
    json: bool,
}

#[derive(Deserialize)]
struct WeatherResponse {
    city: String,
    temperature: f64,
    description: String,
    humidity: u32,
    wind_speed: f64,
}

#[derive(Deserialize)]
struct ErrorResponse {
    detail: String,
}

fn weather_icon(description: &str) -> &'static str {
    let desc = description.to_lowercase();
    if desc.contains("clear") || desc.contains("sunny") {
        "☀️"
    } else if desc.contains("partly") || desc.contains("few clouds") {
        "🌤"
    } else if desc.contains("overcast") || desc.contains("broken") {
        "☁️"
    } else if desc.contains("rain") || desc.contains("drizzle") {
        "🌧"
    } else if desc.contains("thunder") || desc.contains("storm") {
        "⛈"
    } else if desc.contains("snow") || desc.contains("blizzard") {
        "❄️"
    } else if desc.contains("mist") || desc.contains("fog") || desc.contains("haze") {
        "🌫"
    } else {
        "🌡"
    }
}

fn russian_error(status: u16, detail: &str) -> String {
    match status {
        404 => format!("Город не найден: {}", detail),
        422 => format!("Некорректный запрос: {}", detail),
        502 => "Ошибка сервиса погоды (провайдер недоступен). Попробуйте позже.".to_string(),
        503 => "Сервис временно недоступен (превышен лимит запросов). Попробуйте позже.".to_string(),
        504 => "Превышено время ожидания ответа от сервиса. Попробуйте позже.".to_string(),
        500 => "Внутренняя ошибка сервера. Попробуйте позже.".to_string(),
        _ => format!("Ошибка {}: {}", status, detail),
    }
}

fn main() {
    let args = Args::parse();

    let url = format!("http://localhost:8000/weather/{}", args.city);

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .expect("Не удалось создать HTTP-клиент");

    let response = match client.get(&url).send() {
        Ok(r) => r,
        Err(e) => {
            if e.is_connect() || e.is_timeout() {
                eprintln!(
                    "{} Не удалось подключиться к сервису погоды (http://localhost:8000). \
                     Убедитесь, что сервис запущен.",
                    "Ошибка:".red().bold()
                );
            } else {
                eprintln!("{} {}", "Ошибка сети:".red().bold(), e);
            }
            std::process::exit(1);
        }
    };

    let status = response.status().as_u16();

    if args.json {
        // В режиме --json выводим тело ответа как есть
        let text = response.text().unwrap_or_default();
        println!("{}", text);
        if status >= 400 {
            std::process::exit(1);
        }
        return;
    }

    if status == 200 {
        match response.json::<WeatherResponse>() {
            Ok(w) => {
                let icon = weather_icon(&w.description);
                println!(
                    "{} {}: {}°C, {}, влажность {}%, ветер {} м/с",
                    icon,
                    w.city.bold(),
                    format!("{:.0}", w.temperature).yellow().bold(),
                    w.description.cyan(),
                    w.humidity,
                    format!("{:.1}", w.wind_speed).blue(),
                );
            }
            Err(e) => {
                eprintln!("{} Не удалось разобрать ответ: {}", "Ошибка:".red().bold(), e);
                std::process::exit(1);
            }
        }
    } else {
        let detail = response
            .json::<ErrorResponse>()
            .map(|e| e.detail)
            .unwrap_or_else(|_| "Неизвестная ошибка".to_string());

        eprintln!(
            "{} {}",
            "Ошибка:".red().bold(),
            russian_error(status, &detail)
        );
        std::process::exit(1);
    }
}
