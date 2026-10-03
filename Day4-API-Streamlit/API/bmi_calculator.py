from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class BMIRequest(BaseModel):
    weight: float = Field(..., gt=0, description="Weight in kilograms")
    height: float = Field(..., gt=0, description="Height in meters")


class BMIResponse(BaseModel):
    weight: float
    height: float
    bmi: float
    category: str

@app.get("/bmi")
async def root():
    return {"message": "Welcome to the BMI Calculator version 1.0!"}

@app.put("/bmi", response_model=BMIResponse)
async def calculate_bmi(data: BMIRequest):
    bmi = data.weight / (data.height ** 2)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    return {
        "weight": data.weight,
        "height": data.height,
        "bmi": round(bmi, 2),
        "category": category
    }