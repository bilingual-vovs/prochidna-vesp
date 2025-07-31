require('dotenv').config()
const TOKEN = process.env.TOKEN
const MQTT_USER = process.env.MQTT_USER
const MQTT_IP = 'mqtt://' + process.env.MQTT_IP
const MQTT_SUB = process.env.MQTT_SUB

const TelegramBot = require('node-telegram-bot-api')
const fs = require('fs');
const path = require('path');
const bot = new TelegramBot(TOKEN , { polling: true });

const usersFilePath = path.join(__dirname, 'users.json');

const saveUser = (id) => {
    return new Promise((res, rej) => {
        fs.readFile(usersFilePath, (err, data)=>{
            let dat = JSON.parse(data)
            if (dat.includes(id)){
                res(true)
            }
            else{
                dat.push(id)
                fs.writeFile(usersFilePath, JSON.stringify(dat), 'utf-8', (err)=>{
                    if (err) console.error(err)
                    else res(true)
                })
            }
        })
    })
}

const sendAll = (msg) => {
    return new Promise((res, rej) => {
        fs.readFile(usersFilePath, (err, data)=>{
            let dat = JSON.parse(data)
            dat.forEach(id => {
                bot.sendMessage(id, msg)
            });
            res()
        })
    })
}

bot.on('message', (msg) => {
    saveUser(msg.chat.id).then(()=>{
        bot.sendMessage(msg.chat.id, 'Ви підписалися на отримання системних сповіщень тестової проїідної')
    })
});

bot.on('polling_error', (error) => {
    console.error(`[polling_error] ${error.code}: ${error.message}`);
});




const mqtt = require('mqtt');


const options = {
  clientId: `mqtt_${Math.random().toString(16).slice(3)}`, 
  connectTimeout: 4000, 
  username: MQTT_USER,
//   password: 'your_password',
};

console.log('Connecting to MQTT broker...');

const client = mqtt.connect(MQTT_IP, options);

client.on('connect', () => {
  console.log('Successfully connected to MQTT broker!');

  client.subscribe(MQTT_SUB);
});

client.on('error', (error) => {
  console.error('Connection failed:', error);

  client.end();
});

client.on('message', (topic, message) => {

  const messageString = message.toString();
  console.log(`Received message: "${messageString}" on topic: "${topic}"`);
  sendAll(`Received message: "${messageString}" on topic: "${topic}"`)
});