from locust import HttpUser, task, between

class ShortenerUser(HttpUser):
    # пауза между запросами пользователя
    wait_time = between(1, 3)

    def on_start(self):
        # эта штука срабатывает один раз при старте юзера
        # создаем себе одну ссылку, чтобы потом массово по ней кликать
        response = self.client.post("/links/shorten", json={
            "original_url": "https://fastapi.tiangolo.com/"
        })
        if response.status_code == 200:
            self.short_code = response.json().get("short_code")
        else:
            self.short_code = None

    @task(3)
    def redirect_link(self):
        # тестируем чтение
        if self.short_code:
            self.client.get(f"/links/{self.short_code}", allow_redirects=False)

    @task(1)
    def create_new_link(self):
        # тестируем запись
        self.client.post("/links/shorten", json={
            "original_url": "https://github.com/"
        })