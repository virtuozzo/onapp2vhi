from cp_wrapper import OnAppCP

@given('I am a cloud user ({name})')
def step_impl(context, name):
    
    context.cp = OnAppCP(name)
    