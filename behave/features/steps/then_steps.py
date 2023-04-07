from time import sleep

CHECK_FAILED = False # to replace buggy context.failed

use_step_matcher('parse')
@then('CP API ({action}) should return status code {status_code}')
def step_impl(context, action, status_code):
    
    if context.response.status_code != int(status_code):
        assert CHECK_FAILED, "error: status code returned is {actual}, with error message: {error}"\
            .format(actual=str(context.response.status_code), error=context.response.text)

use_step_matcher('re')
@then('I wait for (?P<wait_time>[0-9]+) (?P<frequency>minutes?|seconds?)')
def step_impl(context, wait_time, frequency):
    
    if "minute" in frequency:
        sleep(int(wait_time) * 60)
    else:
        sleep(int(wait_time))

use_step_matcher('parse')
@then('the virtual machine ({name}) is built successfully')
def step_impl(context, name):

    data = context.cp.search("virtual_machines", args=name)

    if data[0]["virtual_machine"]["built"]:
        pass
    else:
        assert CHECK_FAILED, "error: virtual machine is not built"
