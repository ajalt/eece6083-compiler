#ifndef RUNTIME_H
#define RUNTIME_H

extern void validateBooleanOp(int left, char op, int right, int lineno);
extern int getBool();
extern int getInteger();
extern float getFloat();
extern int getString(char*);
extern void putBool(int val);
extern void putInteger(int val);
extern void putFloat(float val);
extern void putString(char* val);

#endif