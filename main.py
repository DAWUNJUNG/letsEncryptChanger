import dotenv
import os
import re
from datetime import date


class autoRenewLetsEncrypt:

    def __init__(self):
        dotenv.load_dotenv(dotenv.find_dotenv())
        self.encryptLivePath = os.getenv('ENCRYPT_PATH') + '/live/' + os.getenv('DOMAIN')
        self.encryptArchivePath = os.getenv('ENCRYPT_PATH') + '/archive/' + os.getenv('DOMAIN')
        self.encryptRenewPath = os.getenv('ENCRYPT_PATH') + '/renew/' + os.getenv('DOMAIN') + '.conf'
        self.domain = os.getenv('DOMAIN')
        self.haproxyPath = os.getenv('HAPROXY_PATH') + '/haproxy.cfg'
        self.todayDate = date.today()

    def start(self):
        try:
            self.renewLetsEncrypt()
            self.makeSitePem()
            self.changeEncryptDirName()
            self.modifyProxyConfig()

            return True
        except():
            return False

    def renewLetsEncrypt(self):
        try:
            # Let's Encrypt 인증서 재발급
            command = "certbot certonly --dns-cloudflare --preferred-challenges dns-01 " \
                      "--dns-cloudflare-propagation-seconds 20 --dns-cloudflare-credentials " \
                      f"/root/.secrets/certbot-cloudflare.ini -d {self.domain} -d *.{self.domain}"

            if str(os.system(command)).find("Error creating new order"):
                return False
            if str(os.system(command)).find("Successfully received certificate."):
                return True

            return False
        except():
            return False

    def makeSitePem(self):
        try:
            # site.pem 파일 생성
            os.system(
                f"cat {self.encryptLivePath}/cert.pem {self.encryptLivePath}/chain.pem {self.encryptLivePath}/privkey.pem > {self.encryptLivePath}/site.pem")
            return True
        except():
            return False

    def changeEncryptDirName(self):
        # ========================================================================================
        # live, archive : mv {ENCRYPT_PATH}{DOMAIN} {ENCRYPT_PATH}{DOMAIN}-{당일날짜(YYYY-MM-DD)}
        # renew : mv {ENCRYPT_PATH}{DOMAIN}.conf {ENCRYPT_PATH}{DOMAIN}-{당일날짜(YYYY-MM-DD)}.conf
        # ========================================================================================
        try:
            # live, archive 디렉토리명 변경
            os.system(f"mv {self.encryptLivePath}/ {self.encryptLivePath}-{self.todayDate}")
            os.system(f"mv {self.encryptArchivePath}/ {self.encryptArchivePath}-{self.todayDate}")
            # renew 파일명 변경
            os.system(f"mv {self.encryptRenewPath}/ {self.encryptRenewPath}-{self.todayDate}")

            return True
        except():
            return False

    def modifyProxyConfig(self):
        try:
            proxy_cfg = ''

            with open(f"{self.haproxyPath}", 'rt') as file:
                proxy_cfg = file.read()
                proxy_cfg = proxy_cfg.replace(f"{self.domain}-2023-07-21", f"{self.domain}-{self.todayDate}")
                re.sub(f"/{self.domain}-^\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])$/",
                       f"{self.domain}-{self.todayDate}", proxy_cfg)
                file.close()

            with open(f"{self.haproxyPath}", 'wt') as file:
                file.write(proxy_cfg)
                file.close()

            os.system('systemctl restart haproxy')

            return True
        except():
            return False


if __name__ == '__main__':
    renewClass = autoRenewLetsEncrypt()
    if renewClass.start():
        print('성공')
    else:
        print('실패')
