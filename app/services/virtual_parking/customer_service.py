from app.services.virtual_parking.service_base import *
from app.module.virtual_parking.customer.db_handler import *
from app.module.virtual_parking.customer.models import *

logger = LogConfig.get_logger()


class VirtualParkingCustomerService(VirtualParkingServiceBase):
    """ every thing about tablat transaction data"""

    def __init__(self, db, user: Account):
        super().__init__(db, user)

    async def get_vp_customer(self, by_pmsp_cusomter_id, by_table_id) -> Union[List[CustomerVpTblRow], ErrorMsgBase]:
        """ 讀取支付平台的場站資訊 """
        tbl = CustomerVpTblHandler(self._db)
        res = await tbl.get(by_pmsp_cusomter_id, by_table_id)
        if isinstance(res, Exception):
            return ApiErrorGeneric.UnexpectedError(f'{res}')
        return res

    async def add_or_update_vp_customer(self, customer_vp_req: CustomerVpApiReq)-> Union[List[CustomerVpTblRow], ErrorMsgBase]:
        """ request 中的 garage id不存在則新增, 存在則 update """
        get_res = await self.get_vp_customer(customer_vp_req.cId, None)
        if isinstance(get_res, ErrorMsgBase):
            return get_res
        if get_res is None or get_res == []:
            return await self.add_vp_customer(customer_vp_req)
        else:
            return await self.update_vp_customer(customer_vp_req)

    async def add_vp_customer(self, customer_vp_req: CustomerVpApiReq) -> Union[List[CustomerVpTblRow], ErrorMsgBase]:
        """ 寫入VP的場站資訊 """

        # 產生要寫入 vp garage table 的資料，並寫入table
        row_data = customer_vp_req.gen_vp_customer_tbl_data()
        tbl = CustomerVpTblHandler(self._db)
        res = await tbl.add(row_data)
        if isinstance(res, Exception):
            return ApiErrorGeneric.UnexpectedError(f'{res}')

        # 讀取剛寫進的 customer_virtual_parking_args table 的資料並且回傳
        check_res = await self.get_vp_customer(None, res.lastrowid)
        if isinstance(check_res, ErrorMsgBase):
            return check_res

        if check_res is None or check_res == []:
            logger.error(f"Can not found the customer pa data we added: last row id: {res.lastrowid}")
            apiError = ApiErrorGeneric.UnexpectedError(f"找不到剛新增的VP業者資料, last row id: {res.lastrowid}")
            return apiError

        return check_res

    async def update_vp_customer(self, customer_vp_req: CustomerVpApiReq) -> Union[List[CustomerVpTblRow], ErrorMsgBase]:
        """ 更新VP的場站資訊 """
        # 產生要寫入 vp customer table 的資料，並寫入table
        row_data = customer_vp_req.gen_vp_customer_tbl_data()
        tbl = CustomerVpTblHandler(self._db)
        res = await tbl.update(row_data)
        if isinstance(res, Exception):
            return ApiErrorGeneric.UnexpectedError(f'{res}')

        # 讀取剛寫進的 customer_virtual_parking_args table 的資料並且回傳
        check_res = await self.get_vp_customer(customer_vp_req.cId, None)
        if isinstance(check_res, ErrorMsgBase):
            return check_res

        if check_res is None or check_res == []:
            logger.error(f"Can not found the virtual parking customer data we updated: customer id: {customer_vp_req.cId}")
            apiError = ApiErrorGeneric.UnexpectedError(f"無法更新，找不到這場站的 Virtual Parking 資料, customer id: {customer_vp_req.cId}")
            return apiError

        return check_res

    async def delete_by_customer_id(self, customer_id):
        """ 刪除VP業者設定 """

        tbl = CustomerVpTblHandler(self._db)
        res = await tbl.delete(customer_id)
        if not isinstance(res, Exception):
            account_id = self._user.account_id
            logger.info(f'Delete virtual parking customer id: {customer_id} by account id: {account_id}')
            self._syslog['create_account_id'] = account_id
            self._syslog['event_id'] = SystemEventType.DELETE_INFO.value
            self._syslog['event_message'] = f'Delete pay_agent customer id: {customer_id} by account id: {account_id}'
            await self._log_service.addlog(self._syslog)
            return True
        else:
            logger.error('Failed to delete virtual parking customer id: {customer_id} by account id: {account_id}')
            return False


