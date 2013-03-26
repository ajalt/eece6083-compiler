#include "stdio.h"
#include "stdlib.h"

char INPUT_BUFFER[1024];

void validateBooleanOp(int left, char op, int right, int lineno) {
    if (left != 0 && left != 1) {
        printf("FATAL ERROR:line %d:Left operand to boolean operator '%c' had illegal value of %d",
               lineno, op, left);
        exit(EXIT_FAILURE);
    }
    if (right != 0 && right != 1) {
        printf("FATAL ERROR:line %d:Right operand to boolean operator '%c' had illegal value of %d",
               lineno, op, left);
        exit(EXIT_FAILURE);
    }
}

int getInteger() {
    int value;
    scanf("%d", &value);
    return value;
}


int getBool() {
    return getInteger();
}

float getFloat() {
    float value;
    scanf("%f", &value);
    return value;
}

char* getString() {
    scanf("%s", INPUT_BUFFER);
    return INPUT_BUFFER;
}

void putInteger(int val){
    printf("%d", val);
}

void putBool(int val) {
    putInteger(val);   
}

void putFloat(float val){
    printf("%f", val);
}

void putString(char *val) {
    printf("%s", val);
}