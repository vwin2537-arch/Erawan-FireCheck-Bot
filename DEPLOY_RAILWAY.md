# 🚂 วิธี Deploy ขึ้น Railway

## 📋 ก่อนเริ่ม
1. สมัครบัญชี Railway ที่ [railway.app](https://railway.app/) (ใช้ GitHub Login ได้เลย)
2. โค้ดของคุณต้องอยู่บน GitHub แล้ว ✅

---

## 🚀 ขั้นตอน Deploy

### ขั้นตอนที่ 1: สร้าง Project ใหม่
1. เข้า [railway.app/dashboard](https://railway.app/dashboard)
2. กด **New Project**
3. เลือก **Deploy from GitHub repo**
4. เลือก Repository **Erawan-FireCheck-Bot**
5. กด **Deploy Now**

---

### ขั้นตอนที่ 2: ใส่ Environment Variables
1. คลิกที่ Service ที่เพิ่งสร้าง (กล่องสี่เหลี่ยม)
2. ไปที่แท็บ **Variables**
3. กด **Raw Editor** แล้ววางข้อความนี้:

```
APP_NAME=FIRMS LINE Bot
APP_ENV=production
DEBUG=false
FIRMS_MAP_KEY=4d3298929ca9dd810386c66effe28c7b
LINE_CHANNEL_ACCESS_TOKEN=jkm/3cMQ/X81XujTHd9HgKbc83QgEeYtBoTl+to2jUNr6Uz/oTTq8sTHJrIZPuniV0aYXJglTceespVYuffxUMvcbnfLy4O2gtbXWlsyc2nYJT1DfZB5QlM0t2a1c5x7Ci/a0k5AtwOd2rZuiPj9qwdB04t89/1O/w1cDnyilFU=
LINE_CHANNEL_SECRET=0dc63d406359a4c79467fa058dbdcce9
LINE_GROUP_ID=C67a8652605c9755ea9c85e8e7cc0504b
TIMEZONE=Asia/Bangkok
AREA_WEST=98.0
AREA_SOUTH=13.4
AREA_EAST=100.0
AREA_NORTH=15.8
```

4. กด **Update Variables**

---

### ขั้นตอนที่ 3: (ถ้าต้องการ) เพิ่ม Database
1. กด **+ New** ในหน้า Project
2. เลือก **Database** > **Add PostgreSQL**
3. Railway จะสร้าง `DATABASE_URL` ให้อัตโนมัติ
4. ไปที่ Service หลัก > Variables > กด **Add Reference** > เลือก `DATABASE_URL` จาก Postgres

*(ถ้าไม่ทำขั้นตอนนี้ มันจะใช้ SQLite ซึ่งก็ใช้งานได้ แต่ข้อมูลจะหายถ้า Redeploy)*

---

### ขั้นตอนที่ 4: รอ Deploy เสร็จ
1. ดูที่แท็บ **Deployments**
2. รอจนขึ้น **Success** (เขียว)
3. กดที่ลิงก์ Domain ด้านบน (เช่น `xxx.up.railway.app`) เพื่อเปิดเว็บ

---

## ✅ เสร็จแล้ว!
- Dashboard: `https://xxx.up.railway.app/`
- Scheduler จะทำงานอัตโนมัติทุก 10 นาที (ช่วง Peak) และทุก 30 นาที (Off-peak)
- ถ้ามี Hotspot ใหม่ บอทจะส่งแจ้งเตือนไปที่กลุ่ม LINE ทันที!

---

## 🐞 แก้ปัญหา
- **ดู Logs**: คลิกที่ Service > แท็บ **Logs**
- **Redeploy**: คลิก **Deployments** > กด **...** > **Redeploy**
