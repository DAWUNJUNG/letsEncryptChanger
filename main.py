import dotenv
import os
import re
from datetime import date, datetime
import smtplib
from email.mime.text import MIMEText


class autoRenewLetsEncrypt:

    def __init__(self):
        dotenv.load_dotenv(dotenv.find_dotenv())
        self.encryptLivePath = os.getenv('ENCRYPT_PATH') + '/live/' + os.getenv('DOMAIN')
        self.encryptArchivePath = os.getenv('ENCRYPT_PATH') + '/archive/' + os.getenv('DOMAIN')
        self.encryptRenewPath = os.getenv('ENCRYPT_PATH') + '/renew/' + os.getenv('DOMAIN') + '.conf'
        self.domain = os.getenv('DOMAIN')
        self.haproxyPath = os.getenv('HAPROXY_PATH') + '/haproxy.cfg'
        self.todayDate = date.today()
        self.log_message = ''

    def start(self):
        renewLetsEncryptResult = False
        makeSitePemResult = False
        changeEncryptDirNameResult = False

        self.log("============ Start Renew Let's Encrypt ============\n")
        renewLetsEncryptResult = self.renewLetsEncrypt()
        self.log("============ End Renew Let's Encrypt ============\n")

        if renewLetsEncryptResult:
            self.log("============ Start Make Site Pem ============\n")
            makeSitePemResult = self.makeSitePem()
            self.log("============ End Make Site Pem ============\n")

        if makeSitePemResult:
            self.log("============ Start Change Encrypt Dir Name ============\n")
            changeEncryptDirNameResult = self.changeEncryptDirName()
            self.log("============ End Change Encrypt Dir Name ============\n")

        if changeEncryptDirNameResult:
            self.log("============ Start Modify Proxy Config ============\n")
            self.modifyProxyConfig()
            self.log("============ End Modify Proxy Config ============\n")

    def renewLetsEncrypt(self):
        try:
            # Let's Encrypt 인증서 재발급
            command = "certbot certonly --dns-cloudflare --preferred-challenges dns-01 " \
                      "--dns-cloudflare-propagation-seconds 20 --dns-cloudflare-credentials " \
                      f"/root/.secrets/certbot-cloudflare.ini -d {self.domain} -d *.{self.domain}"
            command_result = os.popen(command).readline()

            self.log(command_result + '\n')

            if command_result.find("Error creating new order"):
                return False
            if command_result.find("Successfully received certificate."):
                return True

            return False
        except():
            return False

    def makeSitePem(self):
        try:
            # site.pem 파일 생성
            sitePemResult = os.popen(
                f"cat {self.encryptLivePath}/cert.pem {self.encryptLivePath}/chain.pem {self.encryptLivePath}/privkey.pem > {self.encryptLivePath}/site.pem").read()

            self.log(sitePemResult + '\n')

            if sitePemResult != '':
                return False

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
            changeDirLive = os.popen(f"mv {self.encryptLivePath}/ {self.encryptLivePath}-{self.todayDate}").read()
            self.log(changeDirLive + '\n')
            if changeDirLive != '':
                return False
            changeDirArchive = os.popen(
                f"mv {self.encryptArchivePath}/ {self.encryptArchivePath}-{self.todayDate}").read()
            self.log(changeDirArchive + '\n')
            if changeDirArchive != '':
                return False
            # renew 파일명 변경
            changeDirRenew = os.popen(f"mv {self.encryptRenewPath}/ {self.encryptRenewPath}-{self.todayDate}").read()
            self.log(changeDirRenew + '\n')
            if changeDirRenew != '':
                return False

            return True
        except():
            return False

    def modifyProxyConfig(self):
        try:
            proxy_cfg = ''

            with open(f"{self.haproxyPath}", 'rt') as file:
                proxy_cfg = file.read()
                self.log("==== Before Proxy File ====" + '\n')
                self.log(proxy_cfg + '\n')
                proxy_cfg = proxy_cfg.replace(f"{self.domain}-2023-07-21", f"{self.domain}-{self.todayDate}")
                re.sub(f"/{self.domain}-^\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])$/",
                       f"{self.domain}-{self.todayDate}", proxy_cfg)
                self.log("==== After Proxy File ====" + '\n')
                self.log(proxy_cfg + '\n')
                file.close()

            with open(f"{self.haproxyPath}", 'wt') as file:
                file.write(proxy_cfg)
                file.close()

            self.log("==== Proxy Restart ====" + '\n')
            haproxyRestartResult = os.popen('systemctl restart haproxy').read()
            self.log(haproxyRestartResult + '\n')
            if haproxyRestartResult != '':
                return False

            return True
        except():
            return False

    # 메일 발송 function
    def mail_send(self):
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.ehlo()
        smtp.starttls()  # TLS 사용시 필요
        smtp.login(os.getenv('GOOGLE_ID'), os.getenv('GOOGLE_APP_PW'))

        msg = MIMEText(self.log_message)
        msg['To'] = os.getenv('DESTINATION_EMAIL')
        msg['From'] = os.getenv('SOURCE_EMAIL')
        msg['Subject'] = f"{self.domain} 인증서 교체 자동화 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        smtp.sendmail(os.getenv('SOURCE_EMAIL'), os.getenv('DESTINATION_EMAIL'), msg.as_string())

    # 로그 작성 function
    def log(self, message):
        self.log_message = self.log_message + message


if __name__ == '__main__':
    renewClass = autoRenewLetsEncrypt()

    if renewClass.start():
        print('성공')
    else:
        print('실패')

    renewClass.mail_send()