#!/usr/bin/env python

# Import opinel
from opinel.utils import *
from opinel.utils_cloudtrail import *

# Import stock packages
import sys

########################################
##### Main
########################################

def main(args):

    # Configure the debug level
    configPrintException(args.debug)

    # Check version of opinel
    if not check_opinel_version('1.0.4'):
        return 42

    # Check arguments
    profile_name = args.profile[0]
    if not args.bucket_name[0]:
        printError('Error: you need to provide the name of the S3 bucket to deliver log files to.')
        return 42

    # Initialize various lists of regions
    regions = build_region_list('cloudtrail', args.regions)
    disabled_regions = []
    stopped_regions = []
    global_enabled_regions = []

    # By default, we want to enable global services
    include_global_service_events = True

    # Search for AWS credentials
    credentials = read_creds(profile_name)
    if not credentials['AccessKeyId']:
        return 42

    # Iterate through regions and enable CloudTrail and get some info
    printInfo('Fetching CloudTrail status for all regions...')
    for region in regions:
        cloudtrail_client = connect_cloudtrail(credentials, region, True)
        trails = get_trails(cloudtrail_client)
        if len(trails):
            status = cloudtrail_client.get_trail_status(Name = trails[0]['Name'])
            if status['IsLogging']:
                printInfo('CloudTrail is enabled in %s' % region)
            else:
                stopped_regions.append((region, trails[0]['Name']))
            for trail in trails:
                if trail['IncludeGlobalServiceEvents'] == True:
                    include_global_service_events = False
                    global_enabled_regions.append((region, trails[0]['Name']))
        else:
            disabled_regions.append(region)

    # Enable CloudTrail
    if not args.dry_run:
        for region in disabled_regions:
            cloudtrail_client = connect_cloudtrail(credentials, region, True)
            if not cloudtrail_client:
                continue
            # Enable CloudTrails if user says so
            if args.force or prompt_4_yes_no('CloudTrail is disabled in %s. Do you want to enabled it' % region):
                printInfo('Enabling CloudTrail in region %s...' % region)
                name = 'Default'
                cloudtrail_client.create_trail(Name = name, S3BucketName = args.bucket_name[0], S3KeyPrefix = args.s3_key_prefix[0], SnsTopicName = args.sns_topic_name[0], IncludeGlobalServiceEvents = include_global_service_events)
                cloudtrail_client.start_logging(Name = name)
        for region, name in stopped_regions:
            cloudtrail_client = connect_cloudtrail(credentials, region, True)
            if args.force or prompt_4_yes_no('CloudTrail is stopped in %s. Do you want to start it' % region):
                cloudtrail_client.start_logging(Name = name)

    # Fix global services logging enabled in multiple regions
    if not args.dry_run and len(global_enabled_regions) > 1:
        if prompt_4_yes_no('Warning, global services are included in more than one region. Do you want to fix this'):
            regions = []
            for region, name in global_enabled_regions:
                regions.append(region)
            chosen_region = prompt_4_value('Which region ID do you want to enable global services logging in', regions, None, True, True, is_question = True)
            for region, name in global_enabled_regions:
                if region != chosen_region:
                    cloudtrail_client = connect_cloudtrail(credentials, region, True)
                    cloudtrail_client.update_trail(Name = name, IncludeGlobalServiceEvents = False)


########################################
##### Additional arguments
########################################

add_common_argument(parser, {}, 'regions')
add_common_argument(parser, {}, 'dry-run')

parser.add_argument('--s3-bucket-name',
                    dest='bucket_name',
                    default=[ None ],
                    nargs='+',
                    help='Name of the destination S3 bucket.')
parser.add_argument('--s3-key-prefix',
                    dest='s3_key_prefix',
                    default=[ None ],
                    nargs='+',
                    help='Prefix (path) for the log files.')
parser.add_argument('--sns-topic-name',
                    dest='sns_topic_name',
                    default=[ None ],
                    nargs='+',
                    help='Prefix (path) for the log files.')
parser.add_argument('--force',
                    dest='force',
                    default=False,
                    action='store_true',
                    help='Automatically enable CloudTrail if it is not.')


########################################
##### Parse arguments and call main()
########################################

args = parser.parse_args()

if __name__ == '__main__':
    sys.exit(main(args))
