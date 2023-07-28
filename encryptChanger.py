import dotenv
import os
import subprocess
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
        self.haproxyDir = os.getenv('HAPROXY_PATH')
        self.haproxyPath = os.getenv('HAPROXY_PATH') + '/haproxy.cfg'
        self.todayDate = date.today()
        self.logMessage = ''
        self.cloudflareSecretPath = os.getenv('CLOUDFLARE_SECRET_PATH')

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
                      f"{self.cloudflareSecretPath} -d {self.domain} -d *.{self.domain}"

            with subprocess.Popen([command], stdout=subprocess.PIPE, shell=True) as proc:
                commandResult = proc.stdout.readline().decode("utf-8")

            self.log(commandResult + '\n')

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
            proxyCfg = ''

            with open(f"{self.haproxyPath}", 'rt') as file:
                # 기존 Proxy 파일 읽기
                proxyCfg = file.read()

            with open(f"{self.haproxyPath}", 'w+t') as file:
                # 기존 Proxy 백업 파일 생성
                self.log("==== Backup Before Proxy File Create ====" + '\n')
                beforeHaProxy = open(f"{self.haproxyDir}/beforeHaproxyBackup.cfg", 'w+t')
                beforeHaProxy.write(proxyCfg)
                beforeHaProxy.close()

                # SSL 인증서 갱신 후 Dir 변경
                proxyCfg = proxyCfg.replace(f"{self.domain}-2023-07-21", f"{self.domain}-{self.todayDate}")
                re.sub(f"/{self.domain}-^\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])$/",
                       f"{self.domain}-{self.todayDate}", proxyCfg)
                
                # 변경된 Proxy 백업 파일 생성
                self.log("==== Backup After Proxy File Create ====" + '\n')
                afterHaProxy = open(f"{self.haproxyDir}/afterHaproxyBackup.cfg", 'w+t')
                afterHaProxy.write(proxyCfg)
                afterHaProxy.close()

                # 변경된 내용 Proxy 파일에 적용
                file.write(proxyCfg)
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
    def mailSend(self):
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.ehlo()
        smtp.starttls()  # TLS 사용시 필요
        smtp.login(os.getenv('GOOGLE_ID'), os.getenv('GOOGLE_APP_PW'))

        msg = MIMEText(self.logMessage)
        msg['To'] = os.getenv('DESTINATION_EMAIL')
        msg['From'] = os.getenv('SOURCE_EMAIL')
        msg['Subject'] = f"{self.domain} 인증서 교체 자동화 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        smtp.sendmail(os.getenv('SOURCE_EMAIL'), os.getenv('DESTINATION_EMAIL'), msg.as_string())

    # 로그 작성 function
    def log(self, message):
        self.logMessage = self.logMessage + message

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
        rollbackFromBeforeBackup = os.popen(f"cp {self.haproxyDir}/beforeHaproxyBackup.cfg {self.haproxyPath}").read()
        self.log(rollbackFromBeforeBackup + '\n')
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

    renewClass.mailSend()