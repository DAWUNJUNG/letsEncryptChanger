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
        self.encryptRenewalPath = os.getenv('ENCRYPT_PATH') + '/renewal/' + os.getenv('DOMAIN') + '.conf'
        self.domain = os.getenv('DOMAIN')
        self.haproxyPath = os.getenv('HAPROXY_PATH') + '/haproxy.cfg'
        self.todayDate = date.today()
        self.original_proxy_data = ''
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
            command_result = os.popen(command).read()

            self.log(command_result + '\n')

            return True
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
            changeDirLive = os.popen(f"mv {self.encryptLivePath} {self.encryptLivePath}-{self.todayDate}").read()
            self.log(changeDirLive + '\n')
            if changeDirLive != '':
                return False
            changeDirArchive = os.popen(
                f"mv {self.encryptArchivePath} {self.encryptArchivePath}-{self.todayDate}").read()
            self.log(changeDirArchive + '\n')
            if changeDirArchive != '':
                return False
            # renewal 파일명 변경
            changeDirRenewal = os.popen(f"mv {self.encryptRenewalPath} {self.encryptRenewalPath}-{self.todayDate}").read()
            self.log(changeDirRenewal + '\n')
            if changeDirRenewal != '':
                return False

            return True
        except():
            return False

    def modifyProxyConfig(self):
        try:
            proxy_cfg = ''

            with open(f"{self.haproxyPath}", 'rt') as file:
                proxy_cfg = file.read()
                self.original_proxy_data = proxy_cfg
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

    def rollback(self):
        self.log('======= Rollback Start =======\n')

        # live, archive 디렉토리명 변경
        changeDirLive1 = os.popen(f"rm -rf {self.encryptLivePath}").read()
        changeDirLive2 = os.popen(f"rm -rf {self.encryptLivePath}-{self.todayDate}").read()
        self.log(changeDirLive1 + '\n')
        self.log(changeDirLive2 + '\n')

        changeDirArchive1 = os.popen(f"rm -rf {self.encryptArchivePath}").read()
        changeDirArchive2 = os.popen(f"rm -rf {self.encryptArchivePath}-{self.todayDate}").read()
        self.log(changeDirArchive1 + '\n')
        self.log(changeDirArchive2 + '\n')

        # renewal 파일 삭제
        changeDirRenewal1 = os.popen(f"rm -rf {self.encryptRenewalPath}").read()
        changeDirRenewal2 = os.popen(f"rm -rf {self.encryptRenewalPath}-{self.todayDate}").read()
        self.log(changeDirRenewal1 + '\n')
        self.log(changeDirRenewal2 + '\n')

        #proxy data rollback
        with open(f"{self.haproxyPath}", 'wt') as file:
            file.write(self.original_proxy_data)
            file.close()
        haproxyRestartResult = os.popen('systemctl restart haproxy').read()
        self.log(haproxyRestartResult + '\n')

        self.log('======= Rollback End =======\n')

if __name__ == '__main__':
    renewClass = autoRenewLetsEncrypt()

    if renewClass.start():
        print('성공')
    else:
        renewClass.rollback()
        print('실패')

    renewClass.mail_send()