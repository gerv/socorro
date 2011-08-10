#! /usr/bin/env python

import logging
import copy
import datetime as dt
import gzip
import csv
import time
import os.path
import datetime as dt
import contextlib


import socorro.database.database as sdb
import socorro.lib.util as util
import socorro.cron.cron_base as cron
import socorro.lib.config_manager as cm
from socorro.database.cachedIdAccess import IdCache


sql = """
      select
        r.signature,  -- 0
        r.url,        -- 1
        'http://crash-stats.mozilla.com/report/index/' || r.uuid as uuid_url, -- 2
        to_char(r.client_crash_date,'YYYYMMDDHH24MI') as client_crash_date,   -- 3
        to_char(r.date_processed,'YYYYMMDDHH24MI') as date_processed,         -- 4
        r.last_crash, -- 5
        r.product,    -- 6
        r.version,    -- 7
        r.build,      -- 8
        pd.branch,    -- 9
        r.os_name,    --10
        r.os_version, --11
        r.cpu_name || ' | ' || r.cpu_info as cpu_info,   --12
        r.address,    --13
        array(select ba.bug_id from bug_associations ba where ba.signature = r.signature) as bug_list, --14
        r.user_comments, --15
        r.uptime as uptime_seconds, --16
        case when (r.email is NULL OR r.email='') then '' else r.email end as email, --17
        (select sum(adu_count) from raw_adu adu
           where adu.date = '%(now_str)s'
             and pd.product = adu.product_name and pd.version = adu.product_version
             and substring(r.os_name from 1 for 3) = substring(adu.product_os_platform from 1 for 3)
             and r.os_version LIKE '%%'||adu.product_os_version||'%%') as adu_count, --18
        r.topmost_filenames, --19
        case when (r.addons_checked is NULL) then '[unknown]'when (r.addons_checked) then 'checked' else 'not' end as addons_checked, --20
        r.flash_version, --21
        r.hangid, --22
        r.reason, --23
        r.process_type, --24
        r.app_notes, --25
        r.install_age, --26
        rd.duplicate_of --27
      from
        reports r left join productdims pd on r.product = pd.product and r.version = pd.version
            left join reports_duplicates rd on r.uuid = rd.uuid
      where
        '%(yesterday_str)s' <= r.date_processed and r.date_processed < '%(now_str)s'
        %(prod_phrase)s %(ver_phrase)s
      order by 5 -- r.date_processed, munged
      """


#==============================================================================
class DailyCSVDump(cron.CronBase):
    """This class implements the cron job for dumping the daily CSV file"""
    app_name = 'daily_csv'
    app_version = '1.1'
    app_doc = "This app produces a csv file of the current day's crash data"
    #--------------------------------------------------------------------------
    required_config = cm.Namespace()
    required_config.option('day',
               'the date to dump (YYYY-MM-DD)',
               default=dt.date.today().isoformat(),
               from_string_converter=cm.datetime_converter)
    required_config.option('outputPath',
               "file system location to put the 'internal/private' output csv "
               "file",
               default='.')
    required_config.option('publicOutputPath',
               "file system location to put the 'external/public' output csv "
               "file",
               default='.')
    required_config.option('product',
               'the name of the product to track (leave blank for all)',
               default='Firefox')
    required_config.option('version',
               'the name of the version to track (leave blank for all)',
               default='')
    required_config.update(sdb.get_required_config())

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.logger = config.logger

    #--------------------------------------------------------------------------
    def setup_query_parameters(self):
        now = self.config.day + dt.timedelta(1)
        now_str = "%4d-%02d-%02d" % now.timetuple()[:3]
        yesterday = self.config.day
        yesterday_str = "%4d-%02d-%02d" % yesterday.timetuple()[:3]
        self.logger.debug("self.config.day = %s; now = %s; yesterday = %s",
                          self.config.day,
                          now,
                          yesterday)
        prod_phrase = ''
        try:
            if self.config.product != '':
                if ',' in self.config.product:
                    prod_list = [x.strip() for x in
                                               self.config.product.split(',')]
                    prod_phrase = ("and r.product in ('%s')" %
                                     "','".join(prod_list))
                else:
                    prod_phrase = "and r.product = '%s'" % self.config.product
        except Exception:
            util.reportExceptionAndContinue(self.logger)
        ver_phrase = ''
        try:
            if self.config.version != '':
                if ',' in self.config.product:
                    ver_list = [x.strip() for x in
                                              self.config.version.split(',')]
                    ver_phrase = ("and r.version in ('%s')" %
                                     "','".join(ver_list))
                else:
                    ver_phrase = "and r.version = '%s'" % self.config.version
        except Exception:
            util.reportExceptionAndContinue(self.logger)

        return util.DotDict({'now_str': now_str,
                             'yesterday_str': yesterday_str,
                             'prod_phrase': prod_phrase,
                             'ver_phrase': ver_phrase})

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def gzipped_csv_files(self, gzip=gzip, csv=csv):
        private_out_filename = ("%4d%02d%02d-crashdata.csv.gz"
                                % self.config.day.timetuple()[:3])
        private_out_pathname = os.path.join(self.config.outputPath,
                                            private_out_filename)
        private_gzip_file_handle = gzip.open(private_out_pathname, "w")
        private_csv_file_handle = csv.writer(private_gzip_file_handle,
                                             delimiter='\t',
                                             lineterminator='\n')

        pubic_out_filename = ("%4d%02d%02d-pub-crashdata.csv.gz"
                              % self.config.day.timetuple()[:3])
        public_out_pathname = None
        public_out_directory = self.config.get('publicOutputPath')
        public_gzip_file_handle = None
        public_csv_file_handle = None
        if public_out_directory:
            public_out_pathname = os.path.join(public_out_directory,
                                               pubic_out_filename)
            public_gzip_file_handle = gzip.open(public_out_pathname, "w")
            public_csv_file_handle = csv.writer(public_gzip_file_handle,
                                                delimiter='\t',
                                                lineterminator='\n')
        else:
            self.logger.info("Will not create public (bowdlerized) gzip file")
        yield (private_csv_file_handle, public_csv_file_handle)
        private_gzip_file_handle.close()
        if public_gzip_file_handle:
            public_gzip_file_handle.close()

    #--------------------------------------------------------------------------
    def process_crash(self, a_crash_row, id_cache):
        column_value_list = []
        os_name = None
        ooid = ''
        for i, x in enumerate(a_crash_row):
            if x is None:
                x = r'\N'
            if i == 2:
                ooid = x.rsplit('/', 1)[-1]
            if i == 10:  # r.os_name
                x = os_name = x.strip()
            if i == 11:  # r.os_version
                # per bug 519703
                x = id_cache.getAppropriateOsVersion(os_name, x)
                os_name = None
            if i == 14:  # bug_associations.bug_id
                x = ','.join(str(bugid) for bugid in x)
            if i == 15:  # r.user_comments
                x = x.replace('\t', ' ')  # per bug 519703
            if i == 17:  # r.email -- show if the email is likely useful
                # per bugs 529431/519703
                if '@' in x:
                    x = ' yes'
                else:
                    x = ''
            if type(x) == str:
                x = x.strip().replace('\r', '').replace('\n', ' | ')
            column_value_list.append(x)
        return column_value_list

    #--------------------------------------------------------------------------
    def write_row(self, file_handles_tuple, crash_list):
        """
        Write a row to each file: Seen by internal users (full details), and
        external users (bowdlerized)
        """
        private_file_handle, public_file_handle = file_handles_tuple
        # self.logger.debug("Writing crash %s (%s)",crash_list,len(crash_list))
        private_file_handle.writerow(crash_list)
        crash_list[1] = 'URL (removed)'  # remove url
        crash_list[17] = ''  # remove email
        if public_file_handle:
            public_file_handle.writerow(crash_list)

    #--------------------------------------------------------------------------
    def main(self,
             sdb=sdb,
             gzipped_csv_files=gzipped_csv_files,
             IdCache=IdCache,
             write_row=write_row,
             process_crash=process_crash):
        dbConnectionPool = sdb.DatabaseConnectionPool(self.config, self.logger)
        try:
            try:
                db_conn, db_cursor = dbConnectionPool.connectionCursorPair()

                with gzipped_csv_files(self.config) as csv_file_handles_tuple:
                    headers_not_yet_written = True
                    id_cache = IdCache(db_cursor)
                    sql_parameters = setup_query_parameters(self.config)
                    self.logger.debug("self.config.day = %s; now = %s; "
                                      "yesterday = %s",
                                      self.config.day,
                                      sql_parameters.now_str,
                                      sql_parameters.yesterday_str)
                    sql_query = sql % sql_parameters
                    self.logger.debug("SQL is: %s", sql_query)
                    for crash_row in sdb.execute(db_cursor, sql_query):
                        if headers_not_yet_written:
                            write_row(csv_file_handles_tuple,
                                      [x[0] for x in db_cursor.description])
                            headers_not_yet_written = False
                        column_value_list = process_crash(crash_row, id_cache)
                        write_row(csv_file_handles_tuple,
                                  column_value_list)
                        # end for loop over each crash_row
            finally:
                dbConnectionPool.cleanup()
        except:
            util.reportExceptionAndContinue(self.logger)


#------------------------------------------------------------------------------
if __name__ == '__main__':
    import socorro.app.generic_app as gapp
    gapp.main(DailyCSVDump)