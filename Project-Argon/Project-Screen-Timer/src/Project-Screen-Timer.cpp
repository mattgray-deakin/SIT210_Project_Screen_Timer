/******************************************************/
//       THIS IS A GENERATED FILE - DO NOT EDIT       //
/******************************************************/

#include "Particle.h"
#line 1 "e:/Particle_Argon_Folder/Project-Argon/Project-Screen-Timer/src/Project-Screen-Timer.ino"
/*
8-Feb-2015
Jim Brower
bulldoglowell@gmail.com
*/
#include "LiquidCrystal_I2C_Spark.h"

void setup(void);
void ser_recieve();
void read_device_data();
void send_alarm();
void clear_display();
void serial_selector();
void display_data(int index, String name, int time);
void loop(void);
#line 8 "e:/Particle_Argon_Folder/Project-Argon/Project-Screen-Timer/src/Project-Screen-Timer.ino"
LiquidCrystal_I2C *lcd;

const byte char_max = 40;
char ser_rcv[char_max];

boolean datarcv = false;
int publish_counter = 0;


void setup(void)
{
  Serial1.begin(9600);
  lcd = new LiquidCrystal_I2C(0x27, 20, 4);
  lcd->init();
  lcd->backlight();
  lcd->clear();
  lcd->print("Screen Timer Init");
}

void ser_recieve()
{
  static boolean receiving_data = false;
  static byte index = 0;
  char data_starter = '[';
  char data_ender = ']';
  char rx_char;

  while (Serial1.available() > 0 && datarcv == false)
  {
    rx_char = Serial1.read();

    if (receiving_data == true)
    {

      if (rx_char != data_ender)
      {
        ser_rcv[index] = rx_char;
        index++;

        if (index >= char_max)
        {
          index = char_max - 1;
        }
      }

      else
      {
        ser_rcv[index] = '\0';
        receiving_data = false;
        index = 0;
        datarcv = true;
      }
    }

    else if (rx_char == data_starter)
    {
      receiving_data = true;
    }
  }
  
}

void read_device_data(){
  int index, time;
  String name, pub_str;
  bool index_ck, name_ck, time_ck;
  index = -1;
  time = -1;
  name = "";
  // lcd->clear();
  // lcd->print("READING DEVICE DATA");
  delay(2000);
  index_ck = name_ck = time_ck = 0;

  if (time_ck == 0 ){
    while (index_ck == 0){
      ser_recieve();
      if (datarcv == true){
        index = atoi(ser_rcv);
        datarcv = false;
        ser_rcv[0] = '\0';
        if (index != -1) {
          index_ck = 1;
        }
       }
    }

    while (name_ck == 0){
      ser_recieve();
      if (datarcv == true){
        name = ser_rcv;
        datarcv = false;
        ser_rcv[0] = '\0';
        if (name != ""){
          name_ck = 1;
        }
      }
    }

    while (time_ck == 0){
      ser_recieve();
      if (datarcv == true){
        time = atoi(ser_rcv);
        datarcv = false;
        ser_rcv[0] = '\0';
        if (time != -1){
          time_ck = 1;
        }
      }
    }
    if (index < 4){
      display_data(index, name, time);
    }
    publish_counter++;

    if (publish_counter == 20){
      Particle.publish("Dev in Use", name);
    }
  }
}

void send_alarm(){
  String dev_at_limit;
  lcd->clear();
  lcd->print("Device Overtime");
  ser_recieve();
  dev_at_limit = ser_rcv;
  lcd->setCursor(0, 2);
  lcd->print(dev_at_limit);
  Particle.publish("Limit Reached", dev_at_limit);
  ser_rcv[0] = '\0';
  datarcv = false;

}
void clear_display(){
  lcd->clear();
  lcd->setCursor(3, 0);
  lcd->print("Awaiting Data");
  lcd->setCursor(3, 2);
  lcd->print("Or no Devices");
}

void serial_selector(){
  ser_recieve();
  if (datarcv == true){
    if (atoi (ser_rcv) == 1){
      ser_rcv[0] = '\0';
      datarcv = false;
      read_device_data();

    }
    else if (atoi (ser_rcv) == 2){
      ser_rcv[0] = '\0';
      datarcv = false;
      send_alarm();
    }
    else if (atoi (ser_rcv) == 3){
      ser_rcv[0] = '\0';
      clear_display();
      datarcv = false;
    }
    else if (atoi (ser_rcv) == 4){
      ser_rcv[0] = '\0';
      lcd->clear();
      datarcv = false;
    }
    else {
      Serial1.println("Error in Serial Selection");
      ser_rcv[0]='\0';
      datarcv = false;
    }
  }
}

void display_data(int index, String name, int time){
  lcd->setCursor(0, index);
  lcd->print((time / 60));
  lcd->print(" min ");
  lcd->print(name);
}

void loop(void)
{
  serial_selector();
}