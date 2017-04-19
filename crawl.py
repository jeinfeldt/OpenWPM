'''Starts crawls executing defined workload for measurement'''
from automation import TaskManager, CommandSequence

# The list of sites that we wish to crawl
NUM_BROWSERS = 1
DIRECTORY = '~/Desktop/'
SITES = ['http://www.hdm-stuttgart.de']

def load_params(num_browsers):
    """Loads corresponding parameters for defined crawl"""
    manager_params, browser_params = TaskManager.load_default_params(num_browsers)
    # Update browser configuration (use this for per-browser settings)
    for i in xrange(num_browsers):
        browser_params[i]['http_instrument'] = True
        browser_params[i]['disable_flash'] = False
        browser_params[i]['headless'] = True
    # Update TaskManager configuration (use this for crawl-wide settings)
    manager_params['data_directory'] = DIRECTORY
    manager_params['log_directory'] = DIRECTORY
    return manager_params, browser_params

if __name__ == "__main__":
    m_params, b_params = load_params(NUM_BROWSERS)
    manager = TaskManager.TaskManager(m_params, b_params)
    for site in SITES:
        command_sequence = CommandSequence.CommandSequence(site)
        # Start by visiting the page, Commands times out after 60 seconds
        command_sequence.get(sleep=0, timeout=60)
        # dump_profile_cookies/dump_flash_cookies closes the current tab.
        command_sequence.dump_profile_cookies(120)
        # ** = synchronized browsers
        manager.execute_command_sequence(command_sequence, index='**')
    # Shuts down the browsers and waits for the data to finish logging
    manager.close()
