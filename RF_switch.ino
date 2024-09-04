#include <Arduino.h>

// 定义四个控制继电器的GPIO引脚
const int relayPins[] = {13, 12, 14, 27};  // 确保这些引脚支持GPIO输出

void setup() {
  Serial.begin(115200);  // 初始化串口通信
  // 配置GPIO引脚为开漏输出并设置为高阻态（开漏模式下的默认“关闭”状态）
  for (int i = 0; i < 4; i++) 
  {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW); // 初始状态，继电器断开
  }
}

void loop() {
  // 检查是否有串口数据
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');  // 读取一行数据

    // 根据接收到的命令控制继电器
    for (int i = 0; i < 4; i++) {
      if (command == String("ON") + String(i)) 
      {
        digitalWrite(relayPins[i], HIGH); // 开漏输出低电平，继电器吸合
        delay(50);
        digitalWrite(relayPins[i], LOW);
      } 
      else if (command == String("OFF") + String(i)) 
      {
        digitalWrite(relayPins[i], LOW); // 开漏输出高阻态，继电器断开
      }
    }
  }
}

