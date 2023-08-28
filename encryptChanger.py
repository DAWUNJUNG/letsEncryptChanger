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
        self.encryptLiveDir = os.getenv('ENCRYPT_PATH') + '/live/'
        self.encryptLivePath = self.encryptLiveDir + os.getenv('DOMAIN')
        self.encryptArchiveDir = os.getenv('ENCRYPT_PATH') + '/archive/'
        self.encryptArchivePath = self.encryptArchiveDir + os.getenv('DOMAIN')
        self.encryptRenewalDir = os.getenv('ENCRYPT_PATH') + '/renewal/'
        self.encryptRenewalPath = self.encryptRenewalDir + os.getenv('DOMAIN') + '.conf'
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
        modifyProxyConfigResult = False

        self.log("============ Start Renew Let's Encrypt ============\n")
        renewLetsEncryptResult = self.renewLetsEncrypt()
        self.log('\n성공\n' if renewLetsEncryptResult else '\n실패\n')
        self.log("============ End Renew Let's Encrypt ============\n")

        if renewLetsEncryptResult:
            self.log("============ Start Make Site Pem ============\n")
            makeSitePemResult = self.makeSitePem()

            self.log('\n성공\n' if makeSitePemResult else '\n실패\n')
            self.log("============ End Make Site Pem ============\n")

        if makeSitePemResult:
            self.log("============ Start Change Encrypt Dir Name ============\n")
            changeEncryptDirNameResult = self.changeEncryptDirName()
            self.log('\n성공\n' if changeEncryptDirNameResult else '\n실패\n')
            self.log("============ End Change Encrypt Dir Name ============\n")

        if changeEncryptDirNameResult:
            self.log("============ Start Modify Proxy Config ============\n")
            modifyProxyConfigResult = self.modifyProxyConfig()
            self.log('\n성공\n' if modifyProxyConfigResult else '\n실패\n')
            self.log("============ End Modify Proxy Config ============\n")

        if renewLetsEncryptResult and makeSitePemResult and changeEncryptDirNameResult and modifyProxyConfigResult:
            return True
        else:
            return False

    def renewLetsEncrypt(self):
        try:
            # Let's Encrypt 인증서 재발급
            command = "certbot certonly --dns-cloudflare --preferred-challenges dns-01 " \
                      "--dns-cloudflare-propagation-seconds 20 --dns-cloudflare-credentials " \
                      f"{self.cloudflareSecretPath} -d {self.domain} -d *.{self.domain}"

            proc = subprocess.Popen([command], stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
            proc.terminate()

            self.log("output : \n")
            self.log(str(out))
            self.log("\n")
            self.log("error : \n")
            self.log(str(err))
            self.log("\n")

            if 'Successfully received certificate' not in str(out):
                return False

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
            renewalPathSplit = self.encryptRenewalPath.rsplit('.', 1)
            changeDirRenewal = os.popen(f"mv {self.encryptRenewalPath} {renewalPathSplit[0]}-{self.todayDate}.{renewalPathSplit[1]}").read()
            self.log(changeDirRenewal + '\n')
            if changeDirRenewal != '':
                return False

            return True
        except():
            return False

    def delOldProxyFiles(self):
        try:
            self.log('======= Delete Old Proxy Files Start =======\n')

            liveFileList = os.listdir(self.encryptLiveDir)
            archiveFileList = os.listdir(self.encryptArchiveDir)
            renewalFileList = os.listdir(self.encryptRenewalDir)
            renewalPathSplit = self.encryptRenewalPath.rsplit('.', 1)

            # 변경일 디렉토리 삭제 대상에서 제외
            liveFileList.remove(f"{self.encryptLivePath}-{self.todayDate}")
            archiveFileList.remove(f"{self.encryptArchivePath}-{self.todayDate}")
            renewalFileList.remove(f"{renewalPathSplit[0]}-{self.todayDate}.{renewalPathSplit[1]}")

            # live 디렉토리 작업
            changeDirLive1 = os.popen(f"rm -rf {self.encryptLivePath}").read()
            self.log(changeDirLive1 + '\n')
            for dirName in liveFileList:
                # changeDirLive2 = os.popen(f"rm -rf {str(dirName)}").read()
                # self.log(changeDirLive2 + '\n')
                print(str(dirName))

            # archive 디렉토리 작업
            changeDirArchive1 = os.popen(f"rm -rf {self.encryptArchivePath}").read()
            self.log(changeDirArchive1 + '\n')
            for dirName in liveFileList:
                # changeDirArchive2 = os.popen(f"rm -rf {str(dirName)}").read()
                # self.log(changeDirArchive2 + '\n')
                print(str(dirName))

            # renewal 디렉토리 작업
            changeDirRenewal1 = os.popen(f"rm -rf {self.encryptRenewalPath}").read()
            self.log(changeDirRenewal1 + '\n')
            for dirName in liveFileList:
                # changeDirRenewal2 = os.popen(f"rm -rf {str(dirName)}").read()
                # self.log(changeDirRenewal2 + '\n')
                print(str(dirName))

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
                proxyCfg = re.sub("(" + self.domain + "-\d{4}-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01]))", self.domain + "-" + str(self.todayDate), proxyCfg)
                
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
        renewalPathSplit = self.encryptRenewalPath.rsplit('.', 1)
        changeDirRenewal1 = os.popen(f"rm -rf {self.encryptRenewalPath}").read()
        changeDirRenewal2 = os.popen(f"rm -rf {renewalPathSplit[0]}-{self.todayDate}.{renewalPathSplit[1]}").read()
        self.log(changeDirRenewal1 + '\n')
        self.log(changeDirRenewal2 + '\n')

        #proxy data rollback
        if os.path.isfile("{self.haproxyDir}/beforeHaproxyBackup.cfg"):
            rollbackFromBeforeBackup = os.popen(f"cp {self.haproxyDir}/beforeHaproxyBackup.cfg {self.haproxyPath}").read()
            self.log(rollbackFromBeforeBackup + '\n')
            haproxyRestartResult = os.popen('systemctl restart haproxy').read()
            self.log(haproxyRestartResult + '\n')

        self.log('======= Rollback End =======\n')

if __name__ == '__main__':
    renewClass = autoRenewLetsEncrypt()

    renewClass.delOldProxyFiles()

    # if renewClass.start():
    #     print('성공')
    # else:
    #     renewClass.rollback()
    #     print('실패')
    #
    # renewClass.mailSend()