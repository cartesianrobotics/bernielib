#include <Servo.h>
#include <stdlib.h>
#include "HX711.h"

#define INPUT_SIZE 30 // Max expected command size

#define DOUTR 3
#define CLKR 2
#define DOUTL 5
#define CLKL 4

Servo servo1;
HX711 sensor_l;
HX711 sensor_r;

float calibr_factor_r = 1000;
float calibr_factor_l = -1000;

int pos;
// pin 9 to base of Transistor
int powerControl = 9;
int servoPin = 8;
String input_string;

void setup() {
  // Initialize serial port
  Serial.begin(115200);
  Serial.setTimeout(20);
  
  // Wait for serial port to open on native USB devices
  while (!Serial)
  { 
    delay(1);
  }

  // Welcome message
  Serial.println("Arnie's mobile gripper tool");
  Serial.println("Rev. 2.0, 3/21/2020");
  Serial.println("Power servo up: P on");
  Serial.println("Power servo down: P off");
  Serial.println("Rotate servo to 30 degrees: G0 30");
  Serial.println("Servo will actually operate after P on.");
  Serial.println("Tare all load cells: T");
  Serial.println("Tare left load cell: T L");
  Serial.println("Tare right load cell: T R");
  Serial.println("Get left load cell reading: RL");
  Serial.println("Get right load cell reading: RR");

  pinMode(powerControl, OUTPUT);
  servo1.attach(servoPin);

  sensor_l.begin(DOUTL, CLKL);
  sensor_l.set_scale(calibr_factor_l);
  sensor_l.tare();

  sensor_r.begin(DOUTR, CLKR);
  sensor_r.set_scale(calibr_factor_r);
  sensor_r.tare();
}

void loop() {
//  input_string = Serial.readString();
//  pos = input_string.toInt(); //transforming string to int
//  Serial.println(input_string);


  // Get next command from Serial (add 1 for final 0)
  char input[INPUT_SIZE + 1];
  byte size = Serial.readBytes(input, INPUT_SIZE);
  // Add the final 0 to end the C string
  input[size] = 0;

  char* command = strtok(input, " ");

  while (command != 0)
  {
    //Serial.println(command);
    if (strcmp(command, "G0")==0)
    {
      command = strtok(0, " ");
      pos = atoi(command);
      servo1.write(pos);
      Serial.println(pos);
    }
    else if (strcmp(command, "G?")==0)
    {
      Serial.println(pos);
    }
    else if (strcmp(command, "T")==0)
    {
      sensor_l.tare();
      sensor_r.tare();
      Serial.println("ok/n");
    }
    else if (strcmp(command, "T L")==0)
    {
      sensor_l.tare();
      Serial.println("ok/n");
    }
    else if (strcmp(command, "T R")==0)
    {
      sensor_r.tare();
      Serial.println("ok/n");
    }
    else if (strcmp(command, "RL")==0)
    {
      // Uncomment for Bernie SN4; comment the line below
      // Serial.println(sensor_l.get_units()*-1.0);
      Serial.println(sensor_l.get_units());
    }
    else if (strcmp(command, "RR")==0)
    {
      // Uncomment for Bernie SN4; comment the line below
      // Serial.println(sensor_l.get_units()*-1.0);
      Serial.println(sensor_r.get_units());
    }
    else if (strcmp(command, "version")==0)
    {
      Serial.println("Bernie's load cells controller");
    }
    else if (strcmp(command, "version\n")==0)
    {
      Serial.println("Bernie's load cells controller");
    }
    else
    {
      if (strcmp(command, "P") == 0)
      {
        command = strtok(NULL, " ");
        Serial.println(strcmp(command, "on"));
        if (strcmp(command, "on")==0)
        {
          digitalWrite(powerControl, HIGH);
          Serial.println("Servo power ON");
        } 
        else
        {
          digitalWrite(powerControl, LOW);
          Serial.println("Servo power OFF");
        }
      }
    }

//    Serial.println(command);
    command = strtok(0, " ");
  }
  
}
